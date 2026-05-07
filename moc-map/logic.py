"""MOC 知识地图 aApp — 基于 remio 全知识库构建 M.O.C 知识地图。"""

import json
import os
import time
import uuid

from remio_sdk import (
    create_aapp_logger,
    create_note,
    get_aapp_ui_language,
    read_note,
    router,
    run_prompt,
    search_notes,
    get_state,
    set_state,
    syscall,
)

AAPP_DIR = os.environ.get('REMIO_AAPP_DIR', os.getcwd())
DATA_DIR = os.environ.get('REMIO_AAPP_DATA_DIR', os.path.join(os.path.dirname(AAPP_DIR), 'data'))
LOG_DIR = os.environ.get('REMIO_AAPP_LOG_DIR', os.path.join(os.path.dirname(AAPP_DIR), 'log'))
LOGGER = create_aapp_logger('moc-map', LOG_DIR, 'moc-map-logic')

AAPP_ID = 'moc-map'
HISTORY_KEY = 'moc_history'
WECHAT_SUMMARY_FOLDER = '/Volumes/Mac_Data_2T/Clipping/19-ClaudeCode/微信群聊总结'

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _t(zh, en):
    lang = (get_aapp_ui_language() or '').lower()
    return zh if lang.startswith('zh') else en


def _get_history():
    result = get_state(HISTORY_KEY)
    if result.get('ok'):
        data = result.get('data', {})
        return data.get('value', []) if isinstance(data, dict) else []
    return []


def _add_history(entry):
    history = _get_history()
    history.insert(0, entry)
    history = history[:100]
    set_state(HISTORY_KEY, history)


def _find_history(history_id):
    for h in _get_history():
        if h.get('id') == history_id:
            return h
    return None


def _delete_history(history_id):
    history = [h for h in _get_history() if h.get('id') != history_id]
    set_state(HISTORY_KEY, history)


def _read_system_prompt():
    path = os.path.join(AAPP_DIR, 'system.md')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        LOGGER.error('read_system_prompt', str(e), {})
        return ''


def _fetch_domain_notes(domain_type, domain_id, domain_name, query='', limit=50):
    """Fetch notes from a domain (collection, folder, or search)."""
    params = {'limit': limit}
    if domain_type == 'collection':
        params['collection'] = domain_name
        if query:
            params['query'] = query
    elif domain_type == 'folder':
        params['folder'] = domain_id
        if query:
            params['query'] = query
    elif domain_type == 'search':
        params['query'] = query or domain_name

    result = search_notes(params)
    if result.get('ok'):
        return result.get('data', {}).get('items', [])
    return []


def _notes_to_context(notes, max_notes=30):
    """Convert note items into a condensed context string for run_prompt."""
    lines = []
    for i, n in enumerate(notes[:max_notes]):
        note_id = n.get('noteId', '')
        title = n.get('title', _t('未命名', 'Untitled'))
        item_type = n.get('category', n.get('itemType', ''))
        preview = (n.get('preview') or n.get('summary') or '')[:200]
        lines.append(f'{i+1}. [{item_type}] {title} (id:{note_id})\n   {preview}')
    return '\n'.join(lines)


def _generate_moc(notes, domain_name, depth='standard', include_external=True):
    """Call run_prompt to generate a MOC map."""
    system_prompt = _read_system_prompt()
    context = _notes_to_context(notes)

    if not context.strip():
        return _t('未找到足够的笔记材料来构建知识地图。请扩大搜索范围。', 'Not enough notes found to build a knowledge map. Please broaden the scope.')

    depth_instruction = {
        'overview': 'Provide a high-level overview with 3-5 main themes only.',
        'standard': 'Provide a standard analysis with 5-8 themes and moderate detail.',
        'deep': 'Provide an in-depth analysis with all identifiable themes, detailed cross-references, and thorough gap analysis.',
    }.get(depth, 'Provide a standard analysis.')

    external_instruction = ''
    if include_external:
        external_instruction = '\nIMPORTANT: Actively identify cross-domain bridges — concepts, methods, or people that connect to knowledge OUTSIDE this domain.'

    user_prompt = f"""Please build a MOC knowledge map for the following domain.

Domain: {domain_name}
Total notes found: {len(notes)}
Analysis depth: {depth_instruction}{external_instruction}

## Notes in this domain:
{context}

Generate the MOC map now. Use :remio-inlink[title]{{#noteId}} format for note references."""

    result = run_prompt(
        prompt=user_prompt,
        system_prompt=system_prompt,
        stream=False,
        capabilities='create_note',
    )
    if result.get('ok'):
        return result.get('data', {}).get('content', '')
    return f'生成失败：{result.get("error", "未知错误")}'


def _generate_cross_summary(all_notes, domain_names, topic='', time_range=''):
    """Call run_prompt to generate a cross-domain synthesis."""
    system_prompt = _read_system_prompt()

    sections = []
    for domain_name, notes in zip(domain_names, all_notes):
        ctx = _notes_to_context(notes)
        sections.append(f'### Domain: {domain_name}\n{ctx}')

    notes_context = '\n\n'.join(sections)
    topic_instruction = f'\nFocus topic: {topic}' if topic else ''
    time_instruction = f'\nTime range: {time_range}' if time_range else ''

    user_prompt = f"""Please generate a cross-domain synthesis report.

Domains to analyze: {', '.join(domain_names)}{topic_instruction}{time_instruction}

## Notes from each domain:
{notes_context}

Generate the cross-domain synthesis now. Use :remio-inlink[title]{{#noteId}} format for note references."""

    result = run_prompt(
        prompt=user_prompt,
        system_prompt=system_prompt,
        stream=False,
        capabilities='create_note',
    )
    if result.get('ok'):
        return result.get('data', {}).get('content', '')
    return f'生成失败：{result.get("error", "未知错误")}'


def _generate_discovery(notes, time_range=''):
    """Call run_prompt to discover cross-domain connections from recent notes."""
    system_prompt = _read_system_prompt()
    context = _notes_to_context(notes, max_notes=60)

    if not context.strip():
        return _t('未找到最近的新增内容。', 'No recent content found.')

    user_prompt = f"""Please analyze these recently added/modified notes and discover cross-domain connections.

Time range: {time_range or 'recent'}
Total notes: {len(notes)}

## Recent notes:
{context}

Focus on:
1. Cross-domain keyword co-occurrence
2. Potential connections between semantically similar notes in different domains
3. Emerging topics that just started appearing
4. Weak signals worth tracking"""

    result = run_prompt(
        prompt=user_prompt,
        system_prompt=system_prompt,
        stream=False,
        capabilities='create_note',
    )
    if result.get('ok'):
        return result.get('data', {}).get('content', '')
    return f'生成失败：{result.get("error", "未知错误")}'


def _generate_topic_timeline(notes, topic):
    """Call run_prompt to build a topic timeline."""
    system_prompt = _read_system_prompt()
    context = _notes_to_context(notes)

    if not context.strip():
        return _t(f'未找到与「{topic}」相关的笔记。', f'No notes found for "{topic}".')

    user_prompt = f"""Please build a topic timeline for: {topic}

## Related notes:
{context}

Map how this topic evolves across different domains and time periods. Identify key milestones, perspective shifts, and cross-domain connections."""

    result = run_prompt(
        prompt=user_prompt,
        system_prompt=system_prompt,
        stream=False,
        capabilities='create_note',
    )
    if result.get('ok'):
        return result.get('data', {}).get('content', '')
    return f'生成失败：{result.get("error", "未知错误")}'


def _save_moc_note(title, content):
    result = create_note(title=title, content=content)
    if result.get('ok'):
        return result.get('data', {}).get('noteId', '')
    return ''


def _back_button():
    return {
        'kind': 'button',
        'label': _t('🔙 返回首页', '🔙 Back'),
        'action': {'aapp_id': AAPP_ID, 'method': 'GET', 'path': '/', 'params': {}}
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.route('GET', '/')
def _render_main(params):
    """知识全景首页：展示所有 Collection + 文件夹 + 操作入口。"""
    LOGGER.info('aapp.render.main', 'render knowledge panorama', {})

    # Fetch collections
    collections = []
    try:
        coll_result = search_notes({'limit': 1})  # warmup
        # We'll use search_notes with collection filter to discover collections
        known_collections = [
            'Prompt Library',
            'GPT Image 2 提示词',
            'Seedance 2.0 提示词',
            'nano banana 提示词',
        ]
        for coll_name in known_collections:
            r = search_notes({'collection': coll_name, 'limit': 1})
            count = r.get('data', {}).get('total', 0) if r.get('ok') else '?'
            collections.append({'name': coll_name, 'count': count})
    except Exception as e:
        LOGGER.error('fetch_collections', str(e), {})

    # Known folders
    known_folders = [
        {'name': '微信群聊总结', 'path': WECHAT_SUMMARY_FOLDER, 'icon': '💬'},
        {'name': 'Documents', 'path': '/Users/wanglingwei/Documents', 'icon': '📄'},
        {'name': 'Desktop', 'path': '/Users/wanglingwei/Desktop', 'icon': '🖥️'},
        {'name': 'Downloads', 'path': '/Users/wanglingwei/Downloads', 'icon': '📥'},
        {'name': 'Clipping', 'path': '/Volumes/Mac_Data_2T/Clipping', 'icon': '✂️'},
    ]

    components = [
        {'kind': 'text', 'text': '🗺️ MOC ' + _t('知识地图', 'Knowledge Map'), 'heading': 1},
        {'kind': 'text', 'text': _t(
            '发现知识之间的关联，构建你的个人知识地图。',
            'Discover connections in your knowledge and build your personal knowledge map.'
        )},
        {'kind': 'divider'},
    ]

    # Quick actions
    components.append({
        'kind': 'row',
        'items': [
            {
                'kind': 'button',
                'label': '🏗️ ' + _t('构建 MOC', 'Build MOC'),
                'style': 'primary',
                'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/build_moc_ui', 'params': {
                    'domain_type': '', 'domain_id': '', 'domain_name': ''
                }}
            },
            {
                'kind': 'button',
                'label': '🌐 ' + _t('跨域总结', 'Cross-domain'),
                'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/cross_summary_ui', 'params': {
                    'domains': [], 'topic': ''
                }}
            },
            {
                'kind': 'button',
                'label': '🔍 ' + _t('知识发现', 'Discover'),
                'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/discover_ui', 'params': {
                    'time_range': 'last_week'
                }}
            },
        ]
    })
    components.append({'kind': 'divider'})

    # Collections section
    components.append({'kind': 'text', 'text': '📚 ' + _t('Collections', 'Collections'), 'heading': 2})
    coll_items = []
    for c in collections:
        coll_items.append({
            'kind': 'card',
            'title': c['name'],
            'subtitle': f'{c["count"]} ' + _t('篇笔记', 'notes'),
            'actions': [{
                'label': _t('查看地图', 'Map'),
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/domain_map_ui',
                'params': {'domain_type': 'collection', 'domain_id': c['name'], 'domain_name': c['name']}
            }, {
                'label': _t('构建MOC', 'Build MOC'),
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/build_moc_ui',
                'params': {'domain_type': 'collection', 'domain_id': c['name'], 'domain_name': c['name']}
            }]
        })
    if coll_items:
        components.extend(coll_items)
    else:
        components.append({'kind': 'text', 'text': _t('暂无 Collection', 'No collections found')})

    components.append({'kind': 'divider'})

    # Folders section
    components.append({'kind': 'text', 'text': '📁 ' + _t('同步文件夹', 'Sync Folders'), 'heading': 2})
    for f in known_folders:
        components.append({
            'kind': 'card',
            'title': f'{f["icon"]} {f["name"]}',
            'subtitle': f['path'],
            'actions': [{
                'label': _t('查看地图', 'Map'),
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/domain_map_ui',
                'params': {'domain_type': 'folder', 'domain_id': f['path'], 'domain_name': f['name']}
            }, {
                'label': _t('构建MOC', 'Build MOC'),
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/build_moc_ui',
                'params': {'domain_type': 'folder', 'domain_id': f['path'], 'domain_name': f['name']}
            }]
        })

    components.append({'kind': 'divider'})
    components.append({
        'kind': 'button',
        'label': _t('📑 我的 MOC 历史', '📑 My MOC History'),
        'action': {'aapp_id': AAPP_ID, 'method': 'GET', 'path': '/moc_list_ui', 'params': {}}
    })

    return {'components': components}


@router.route('POST', '/domain_map_ui')
def _render_domain_map(params):
    """展示选定域内的主题分布。"""
    domain_type = params.get('domain_type', '')
    domain_id = params.get('domain_id', '')
    domain_name = params.get('domain_name', '')
    query = params.get('query', '')

    LOGGER.info('aapp.domain_map', f'domain: {domain_name}', {'domain_type': domain_type})

    notes = _fetch_domain_notes(domain_type, domain_id, domain_name, query, limit=50)

    components = [
        {'kind': 'text', 'text': f'📍 {domain_name}', 'heading': 1},
        {'kind': 'text', 'text': _t(f'找到 {len(notes)} 篇笔记', f'{len(notes)} notes found')},
        {'kind': 'divider'},
    ]

    if not notes:
        components.append({'kind': 'text', 'text': _t('该域暂无笔记，请选择其他域。', 'No notes in this domain. Please choose another.')})
        components.append(_back_button())
        return {'components': components}

    # Show note list as cards (grouped preview)
    items = []
    for n in notes[:20]:
        title = n.get('title', _t('未命名', 'Untitled'))
        note_id = n.get('noteId', '')
        item_type = n.get('category', n.get('itemType', ''))
        preview = (n.get('preview') or '')[:100]
        items.append({
            'title': title,
            'description': preview,
            'badge': item_type,
            'actions': [{
                'label': _t('查看', 'View'),
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/detail_ui',
                'params': {}  # note detail via open_target
            }]
        })

    if items:
        components.append({'kind': 'list', 'items': items})

    components.append({'kind': 'divider'})
    components.append({
        'kind': 'row',
        'items': [
            {
                'kind': 'button',
                'label': '🏗️ ' + _t('构建 MOC', 'Build MOC'),
                'style': 'primary',
                'action': {
                    'aapp_id': AAPP_ID,
                    'method': 'POST',
                    'path': '/build_moc_ui',
                    'params': {
                        'domain_type': domain_type,
                        'domain_id': domain_id,
                        'domain_name': domain_name,
                        'query': query,
                    }
                }
            },
            _back_button(),
        ]
    })

    return {'components': components}


@router.route('POST', '/build_moc_ui')
def _build_moc(params):
    """构建 MOC 知识地图。"""
    domain_type = params.get('domain_type', '')
    domain_id = params.get('domain_id', '')
    domain_name = params.get('domain_name', '')
    query = params.get('query', '')
    depth = params.get('depth', 'standard')
    include_external = params.get('include_external', True)

    # If domain info is missing, show a form to collect it
    if not domain_name:
        return _render_build_moc_form()

    LOGGER.info('aapp.build_moc', f'building MOC for {domain_name}', {
        'domain_type': domain_type, 'depth': depth
    })

    notes = _fetch_domain_notes(domain_type, domain_id, domain_name, query, limit=50)

    if len(notes) < 3:
        return {
            'components': [
                {'kind': 'text', 'text': f'⚠️ {_t("笔记数量不足（找到 " + str(len(notes)) + " 篇），建议至少 3 篇以上才能构建有意义的 MOC。", "Not enough notes (" + str(len(notes)) + " found). At least 3 recommended for a meaningful MOC.")}'},
                {'kind': 'divider'},
                {
                    'kind': 'input',
                    'key': 'query',
                    'label': _t('添加搜索关键词扩大范围', 'Add keywords to broaden scope'),
                    'value': query,
                },
                {
                    'kind': 'button',
                    'label': _t('重试', 'Retry'),
                    'style': 'primary',
                    'action': {
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/build_moc_ui',
                        'params': {
                            'domain_type': domain_type,
                            'domain_id': domain_id,
                            'domain_name': domain_name,
                        }
                    }
                },
                _back_button(),
            ]
        }

    # Generate MOC
    moc_content = _generate_moc(notes, domain_name, depth, include_external)

    # Save to history
    history_id = str(uuid.uuid4())
    save_title = f'🗺️ {domain_name} ' + _t('知识地图', 'Knowledge Map')
    saved_note_id = _save_moc_note(save_title, moc_content)
    save_status = _t('✅ 已自动保存', '✅ Auto-saved') if saved_note_id else _t('⚠️ 自动保存失败', '⚠️ Auto-save failed')

    _add_history({
        'id': history_id,
        'type': 'moc',
        'domain_type': domain_type,
        'domain_name': domain_name,
        'notes_count': len(notes),
        'depth': depth,
        'content': moc_content,
        'saved_note_id': saved_note_id,
        'created_at': int(time.time()),
    })

    return {
        'components': [
            {'kind': 'text', 'text': f'🗺️ {domain_name} ' + _t('知识地图', 'Knowledge Map'), 'heading': 1},
            {'kind': 'text', 'text': f'{save_status} · {_t(str(len(notes)) + " 篇笔记", str(len(notes)) + " notes")}'},
            {'kind': 'divider'},
            {'kind': 'text', 'text': moc_content},
            {'kind': 'divider'},
            {
                'kind': 'row',
                'items': [
                    {
                        'kind': 'button',
                        'label': _t('🏗️ 构建新 MOC', '🏗️ New MOC'),
                        'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/build_moc_ui', 'params': {}}
                    },
                    _back_button(),
                ]
            },
        ]
    }


def _render_build_moc_form():
    """Show form to collect domain info for MOC building."""
    return {
        'components': [
            {'kind': 'text', 'text': '🏗️ ' + _t('构建 MOC 知识地图', 'Build MOC Knowledge Map'), 'heading': 1},
            {'kind': 'text', 'text': _t('选择一个知识域来构建知识地图。', 'Choose a knowledge domain to build a knowledge map.')},
            {'kind': 'divider'},
            {
                'kind': 'select',
                'key': 'domain_type',
                'label': _t('域类型', 'Domain Type'),
                'options': [
                    {'value': 'collection', 'label': _t('Collection', 'Collection')},
                    {'value': 'folder', 'label': _t('同步文件夹', 'Sync Folder')},
                    {'value': 'search', 'label': _t('关键词搜索', 'Keyword Search')},
                ],
                'value': 'collection'
            },
            {
                'kind': 'input',
                'key': 'domain_name',
                'label': _t('域名称 / 关键词', 'Domain Name / Keywords'),
            },
            {
                'kind': 'select',
                'key': 'depth',
                'label': _t('分析深度', 'Analysis Depth'),
                'options': [
                    {'value': 'overview', 'label': _t('概览（3-5 个主题）', 'Overview (3-5 themes)')},
                    {'value': 'standard', 'label': _t('标准（5-8 个主题）', 'Standard (5-8 themes)')},
                    {'value': 'deep', 'label': _t('深度（全部主题 + 详细关联）', 'Deep (all themes + details)')},
                ],
                'value': 'standard'
            },
            {
                'kind': 'choice',
                'key': 'include_external',
                'label': _t('发现域外关联', 'Discover external bridges'),
                'multiple': False,
                'options': [_t('是', 'Yes'), _t('否', 'No')],
                'value': [_t('是', 'Yes')],
            },
            {'kind': 'divider'},
            {
                'kind': 'button',
                'label': _t('🏗️ 开始构建', '🏗️ Build Now'),
                'style': 'primary',
                'action': {
                    'aapp_id': AAPP_ID,
                    'method': 'POST',
                    'path': '/build_moc_ui',
                    'params': {
                        'domain_type': '',
                        'domain_id': '',
                        'domain_name': '',
                        'depth': 'standard',
                        'include_external': True,
                    }
                }
            },
            _back_button(),
        ]
    }


@router.route('POST', '/build_moc_from_note_ui')
def _build_moc_from_note(params):
    """从内容动作扩展触发。"""
    note_id = (params.get('note_id') or params.get('context_note_id') or '').strip()
    if not note_id:
        return {
            'components': [
                {'kind': 'text', 'text': '⚠️ ' + _t('无法获取笔记 ID', 'Cannot determine note ID')},
                _back_button(),
            ]
        }

    note_result = read_note(note_id)
    if not note_result.get('ok'):
        return {
            'components': [
                {'kind': 'text', 'text': '⚠️ ' + _t('无法读取笔记', 'Failed to read note')},
                _back_button(),
            ]
        }

    note_data = note_result.get('data', {})
    title = note_data.get('title', '')
    collections = note_data.get('collections', [])

    # If the note belongs to a collection, use that as domain
    if collections:
        coll_name = collections[0].get('name', '') if isinstance(collections[0], dict) else collections[0]
        return _build_moc({
            'domain_type': 'collection',
            'domain_id': coll_name,
            'domain_name': coll_name,
            'depth': 'standard',
            'include_external': True,
        })

    # Fallback: use note title as search query
    return _build_moc({
        'domain_type': 'search',
        'domain_id': '',
        'domain_name': title,
        'query': title,
        'depth': 'standard',
        'include_external': True,
    })


@router.route('POST', '/build_moc_shortcut')
def _build_moc_shortcut(params):
    """从 <<moc 快捷命令触发。"""
    user_input = (params.get('input') or '').strip()
    if not user_input:
        return _render_build_moc_form()

    # Treat input as a search query
    return _build_moc({
        'domain_type': 'search',
        'domain_id': '',
        'domain_name': user_input,
        'query': user_input,
        'depth': 'standard',
        'include_external': True,
    })


@router.route('POST', '/cross_summary_ui')
def _cross_summary(params):
    """跨域深度总结。"""
    domains = params.get('domains', [])
    topic = (params.get('topic') or '').strip()
    time_range = params.get('time_range', '')

    # If no domains provided, show the form
    if not domains:
        return {
            'components': [
                {'kind': 'text', 'text': '🌐 ' + _t('跨域深度总结', 'Cross-Domain Synthesis'), 'heading': 1},
                {'kind': 'text', 'text': _t('选择两个或多个知识域进行跨域分析。', 'Select 2+ domains for cross-domain analysis.')},
                {'kind': 'divider'},
                {
                    'kind': 'input',
                    'key': 'domains_text',
                    'label': _t('域名称（逗号分隔，如：GPT Image 2 提示词, Seedance 2.0 提示词）', 'Domain names (comma-separated)'),
                    'placeholder': 'GPT Image 2 提示词, Seedance 2.0 提示词',
                },
                {
                    'kind': 'input',
                    'key': 'topic',
                    'label': _t('聚焦主题（可选）', 'Focus topic (optional)'),
                },
                {
                    'kind': 'select',
                    'key': 'time_range',
                    'label': _t('时间范围', 'Time Range'),
                    'options': [
                        {'value': '', 'label': _t('全部', 'All')},
                        {'value': 'last_week', 'label': _t('最近一周', 'Last week')},
                        {'value': 'last_month', 'label': _t('最近一月', 'Last month')},
                    ],
                    'value': ''
                },
                {'kind': 'divider'},
                {
                    'kind': 'button',
                    'label': _t('🌐 开始分析', '🌐 Analyze'),
                    'style': 'primary',
                    'action': {
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/cross_summary_ui',
                        'params': {'domains': [], 'topic': '', 'time_range': ''}
                    }
                },
                _back_button(),
            ]
        }

    # Parse domains if it's a string
    if isinstance(domains, str):
        domains = [{'domain_type': 'collection', 'domain_id': d.strip(), 'domain_name': d.strip()} for d in domains.split(',') if d.strip()]
    if isinstance(domains, list) and len(domains) > 0 and isinstance(domains[0], str):
        domains = [{'domain_type': 'collection', 'domain_id': d.strip(), 'domain_name': d.strip()} for d in domains if d.strip()]

    # Handle form submission where domains_text is provided instead
    domains_text = params.get('domains_text', '')
    if domains_text and not domains:
        domains = [{'domain_type': 'collection', 'domain_id': d.strip(), 'domain_name': d.strip()} for d in domains_text.split(',') if d.strip()]

    if len(domains) < 2:
        return {
            'components': [
                {'kind': 'text', 'text': '⚠️ ' + _t('请至少选择两个域', 'Please select at least 2 domains')},
                _back_button(),
            ]
        }

    LOGGER.info('aapp.cross_summary', f'cross-domain: {[d["domain_name"] for d in domains]}', {})

    # Fetch notes from each domain
    all_notes = []
    domain_names = []
    for d in domains:
        notes = _fetch_domain_notes(
            d.get('domain_type', 'collection'),
            d.get('domain_id', ''),
            d.get('domain_name', ''),
            limit=30
        )
        all_notes.append(notes)
        domain_names.append(d.get('domain_name', ''))

    # Generate cross-domain summary
    content = _generate_cross_summary(all_notes, domain_names, topic, time_range)

    # Save
    history_id = str(uuid.uuid4())
    save_title = f'🌐 {" × ".join(domain_names)} ' + _t('跨域总结', 'Cross-domain Summary')
    saved_note_id = _save_moc_note(save_title, content)

    _add_history({
        'id': history_id,
        'type': 'cross_summary',
        'domain_names': domain_names,
        'topic': topic,
        'content': content,
        'saved_note_id': saved_note_id,
        'created_at': int(time.time()),
    })

    return {
        'components': [
            {'kind': 'text', 'text': f'🌐 {" × ".join(domain_names)}', 'heading': 1},
            {'kind': 'text', 'text': _t('跨域深度总结', 'Cross-Domain Synthesis')},
            {'kind': 'divider'},
            {'kind': 'text', 'text': content},
            {'kind': 'divider'},
            {
                'kind': 'row',
                'items': [
                    {
                        'kind': 'button',
                        'label': _t('🌐 新的跨域分析', '🌐 New Analysis'),
                        'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/cross_summary_ui', 'params': {}}
                    },
                    _back_button(),
                ]
            },
        ]
    }


@router.route('POST', '/discover_ui')
def _discover(params):
    """知识发现：扫描最近新增内容。"""
    time_range = params.get('time_range', 'last_week')
    scope = params.get('scope', 'all')

    if not time_range:
        # Show form
        return {
            'components': [
                {'kind': 'text', 'text': '🔍 ' + _t('知识发现', 'Knowledge Discovery'), 'heading': 1},
                {'kind': 'text', 'text': _t('扫描最近新增内容，自动发现跨域关联和弱信号。', 'Scan recent content to discover cross-domain connections and weak signals.')},
                {'kind': 'divider'},
                {
                    'kind': 'select',
                    'key': 'time_range',
                    'label': _t('时间范围', 'Time Range'),
                    'options': [
                        {'value': 'last_week', 'label': _t('最近一周', 'Last week')},
                        {'value': 'last_month', 'label': _t('最近一月', 'Last month')},
                    ],
                    'value': 'last_week'
                },
                {
                    'kind': 'button',
                    'label': _t('🔍 开始扫描', '🔍 Scan'),
                    'style': 'primary',
                    'action': {
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/discover_ui',
                        'params': {'time_range': 'last_week', 'scope': 'all'}
                    }
                },
                _back_button(),
            ]
        }

    LOGGER.info('aapp.discover', f'time_range: {time_range}', {})

    # Calculate time filter
    now = int(time.time())
    if time_range == 'last_week':
        start_time = now - 7 * 86400
    else:
        start_time = now - 30 * 86400

    start_date = time.strftime('%Y-%m-%d', time.localtime(start_time))

    # Fetch recent notes
    result = search_notes({
        'sort_by': 'modified',
        'limit': 60,
        'time_filter': {'start': start_date},
    })

    notes = result.get('data', {}).get('items', []) if result.get('ok') else []

    if len(notes) < 3:
        return {
            'components': [
                {'kind': 'text', 'text': _t(f'最近{time_range}内容较少（{len(notes)}篇），暂无足够的发现。', f'Recent content is sparse ({len(notes)} notes). Not enough for discovery.')},
                _back_button(),
            ]
        }

    content = _generate_discovery(notes, time_range)

    # Save
    history_id = str(uuid.uuid4())
    save_title = f'🔍 ' + _t('知识发现报告', 'Knowledge Discovery Report') + f' ({time_range})'
    saved_note_id = _save_moc_note(save_title, content)

    _add_history({
        'id': history_id,
        'type': 'discovery',
        'time_range': time_range,
        'notes_count': len(notes),
        'content': content,
        'saved_note_id': saved_note_id,
        'created_at': int(time.time()),
    })

    return {
        'components': [
            {'kind': 'text', 'text': '🔍 ' + _t('知识发现报告', 'Knowledge Discovery Report'), 'heading': 1},
            {'kind': 'text', 'text': f'{time_range} · {len(notes)} ' + _t('篇笔记', 'notes')},
            {'kind': 'divider'},
            {'kind': 'text', 'text': content},
            {'kind': 'divider'},
            {
                'kind': 'row',
                'items': [
                    {
                        'kind': 'button',
                        'label': _t('🔍 再次扫描', '🔍 Scan Again'),
                        'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/discover_ui', 'params': {}}
                    },
                    _back_button(),
                ]
            },
        ]
    }


@router.route('POST', '/topic_timeline_ui')
def _topic_timeline(params):
    """话题时间线。"""
    topic = (params.get('topic') or '').strip()

    if not topic:
        return {
            'components': [
                {'kind': 'text', 'text': '📈 ' + _t('话题时间线', 'Topic Timeline'), 'heading': 1},
                {'kind': 'text', 'text': _t('输入话题关键词，展示其在不同域的讨论轨迹。', 'Enter a topic keyword to see its trajectory across domains.')},
                {'kind': 'divider'},
                {
                    'kind': 'input',
                    'key': 'topic',
                    'label': _t('话题关键词', 'Topic Keyword'),
                    'placeholder': 'AI Agent / 提示词 / ...',
                },
                {
                    'kind': 'button',
                    'label': _t('📈 生成时间线', '📈 Generate Timeline'),
                    'style': 'primary',
                    'action': {
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/topic_timeline_ui',
                        'params': {'topic': ''}
                    }
                },
                _back_button(),
            ]
        }

    LOGGER.info('aapp.topic_timeline', f'topic: {topic}', {})

    result = search_notes({'query': topic, 'limit': 40})
    notes = result.get('data', {}).get('items', []) if result.get('ok') else []

    content = _generate_topic_timeline(notes, topic)

    history_id = str(uuid.uuid4())
    save_title = f'📈 {topic} ' + _t('话题时间线', 'Topic Timeline')
    saved_note_id = _save_moc_note(save_title, content)

    _add_history({
        'id': history_id,
        'type': 'timeline',
        'topic': topic,
        'content': content,
        'saved_note_id': saved_note_id,
        'created_at': int(time.time()),
    })

    return {
        'components': [
            {'kind': 'text', 'text': f'📈 {topic}', 'heading': 1},
            {'kind': 'text', 'text': _t('话题时间线', 'Topic Timeline')},
            {'kind': 'divider'},
            {'kind': 'text', 'text': content},
            {'kind': 'divider'},
            {
                'kind': 'row',
                'items': [
                    {
                        'kind': 'button',
                        'label': _t('📈 新话题', '📈 New Topic'),
                        'action': {'aapp_id': AAPP_ID, 'method': 'POST', 'path': '/topic_timeline_ui', 'params': {}}
                    },
                    _back_button(),
                ]
            },
        ]
    }


@router.route('GET', '/moc_list_ui')
def _moc_list(params):
    """列出所有已生成的 MOC 笔记。"""
    result = search_notes({'query': '🗺️ MOC 知识地图', 'limit': 20})
    notes = result.get('data', {}).get('items', []) if result.get('ok') else []

    components = [
        {'kind': 'text', 'text': '📑 ' + _t('我的 MOC 历史', 'My MOC History'), 'heading': 1},
    ]

    history = _get_history()
    if history:
        for h in history[:20]:
            h_type = h.get('type', 'moc')
            type_icon = {'moc': '🗺️', 'cross_summary': '🌐', 'discovery': '🔍', 'timeline': '📈'}.get(h_type, '📄')
            domain = h.get('domain_name', '') or h.get('topic', '') or ', '.join(h.get('domain_names', []))
            ts = h.get('created_at', 0)
            time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts)) if ts else ''
            saved = h.get('saved_note_id', '')
            status = '✅' if saved else '⚠️'

            components.append({
                'kind': 'card',
                'title': f'{type_icon} {status} {domain}',
                'subtitle': f'{time_str} · {h.get("notes_count", "?")} {_t("篇", "notes")}',
                'actions': [
                    {
                        'label': _t('查看', 'View'),
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/detail_ui',
                        'params': {'history_id': h.get('id', '')}
                    },
                    {
                        'label': _t('删除', 'Delete'),
                        'aapp_id': AAPP_ID,
                        'method': 'POST',
                        'path': '/delete_ui',
                        'params': {'history_id': h.get('id', '')}
                    },
                ]
            })
    else:
        components.append({'kind': 'text', 'text': _t('暂无 MOC 记录', 'No MOC records yet')})

    components.append({'kind': 'divider'})
    components.append(_back_button())

    return {'components': components}


@router.route('POST', '/detail_ui')
def _render_detail(params):
    """查看一条 MOC 历史详情。"""
    history_id = (params.get('history_id') or '').strip()
    entry = _find_history(history_id)

    if not entry:
        return {
            'components': [
                {'kind': 'text', 'text': '⚠️ ' + _t('未找到该记录', 'Record not found')},
                _back_button(),
            ]
        }

    domain = entry.get('domain_name', '') or entry.get('topic', '') or ', '.join(entry.get('domain_names', []))
    components = [
        {'kind': 'text', 'text': f'📄 {domain}', 'heading': 1},
        {'kind': 'divider'},
        {'kind': 'text', 'text': entry.get('content', '')},
        {'kind': 'divider'},
    ]

    buttons = []
    if not entry.get('saved_note_id'):
        buttons.append({
            'kind': 'button',
            'label': _t('💾 保存为笔记', '💾 Save as Note'),
            'action': {
                'aapp_id': AAPP_ID,
                'method': 'POST',
                'path': '/save_moc_ui',
                'params': {'history_id': history_id}
            }
        })

    buttons.append({
        'kind': 'button',
        'label': _t('📑 返回列表', '📑 Back to List'),
        'action': {'aapp_id': AAPP_ID, 'method': 'GET', 'path': '/moc_list_ui', 'params': {}}
    })
    components.append({'kind': 'row', 'items': buttons})

    return {'components': components}


@router.route('POST', '/save_moc_ui')
def _save_moc(params):
    """保存 MOC 为 remio 笔记。"""
    history_id = (params.get('history_id') or '').strip()
    entry = _find_history(history_id)

    if not entry:
        return {
            'components': [
                {'kind': 'text', 'text': '⚠️ ' + _t('未找到该记录', 'Record not found')},
            ]
        }

    if entry.get('saved_note_id'):
        return {
            'components': [
                {'kind': 'text', 'text': '✅ ' + _t('该记录已保存', 'Already saved')},
                {
                    'kind': 'button',
                    'label': _t('打开笔记', 'Open Note'),
                    'open_target': f'note://{entry["saved_note_id"]}',
                },
            ]
        }

    domain = entry.get('domain_name', '') or entry.get('topic', '') or ', '.join(entry.get('domain_names', []))
    h_type = entry.get('type', 'moc')
    type_prefix = {'moc': '🗺️', 'cross_summary': '🌐', 'discovery': '🔍', 'timeline': '📈'}.get(h_type, '📄')
    title = f'{type_prefix} {domain} ' + _t('知识地图', 'Knowledge Map')

    saved_note_id = _save_moc_note(title, entry.get('content', ''))

    if saved_note_id:
        history = _get_history()
        for h in history:
            if h.get('id') == history_id:
                h['saved_note_id'] = saved_note_id
                break
        set_state(HISTORY_KEY, history)

    status = '✅ ' + _t('保存成功', 'Saved') if saved_note_id else '⚠️ ' + _t('保存失败', 'Save failed')

    components = [
        {'kind': 'text', 'text': status},
    ]
    if saved_note_id:
        components.append({
            'kind': 'button',
            'label': _t('打开笔记', 'Open Note'),
            'open_target': f'note://{saved_note_id}',
        })
    components.append({
        'kind': 'button',
        'label': _t('📑 返回列表', '📑 Back to List'),
        'action': {'aapp_id': AAPP_ID, 'method': 'GET', 'path': '/moc_list_ui', 'params': {}}
    })

    return {'components': components}


@router.route('POST', '/delete_ui')
def _delete(params):
    """删除一条历史记录。"""
    history_id = (params.get('history_id') or '').strip()
    if history_id:
        _delete_history(history_id)

    return {
        'components': [
            {'kind': 'text', 'text': '✅ ' + _t('已删除', 'Deleted')},
            {
                'kind': 'button',
                'label': _t('📑 返回列表', '📑 Back to List'),
                'action': {'aapp_id': AAPP_ID, 'method': 'GET', 'path': '/moc_list_ui', 'params': {}}
            },
        ]
    }


@router.route('GET', '/_menu')
def _menu(params):
    """动态菜单。"""
    return {
        'components': [
            {'kind': 'text', 'text': '🗺️ ' + _t('MOC 知识地图', 'MOC Knowledge Map'), 'heading': 2},
            {
                'kind': 'list',
                'items': [
                    {
                        'title': '🏗️ ' + _t('构建 MOC', 'Build MOC'),
                        'description': _t('为选定知识域构建知识地图', 'Build a knowledge map for a domain'),
                        'actions': [{
                            'label': _t('开始', 'Start'),
                            'aapp_id': AAPP_ID,
                            'method': 'POST',
                            'path': '/build_moc_ui',
                            'params': {}
                        }]
                    },
                    {
                        'title': '🌐 ' + _t('跨域总结', 'Cross-domain'),
                        'description': _t('跨域深度合成分析', 'Cross-domain deep synthesis'),
                        'actions': [{
                            'label': _t('开始', 'Start'),
                            'aapp_id': AAPP_ID,
                            'method': 'POST',
                            'path': '/cross_summary_ui',
                            'params': {}
                        }]
                    },
                    {
                        'title': '🔍 ' + _t('知识发现', 'Discover'),
                        'description': _t('扫描跨域关联和弱信号', 'Scan for cross-domain connections'),
                        'actions': [{
                            'label': _t('开始', 'Start'),
                            'aapp_id': AAPP_ID,
                            'method': 'POST',
                            'path': '/discover_ui',
                            'params': {}
                        }]
                    },
                    {
                        'title': '📈 ' + _t('话题时间线', 'Timeline'),
                        'description': _t('追踪话题在不同域的演进', 'Track topic evolution across domains'),
                        'actions': [{
                            'label': _t('开始', 'Start'),
                            'aapp_id': AAPP_ID,
                            'method': 'POST',
                            'path': '/topic_timeline_ui',
                            'params': {}
                        }]
                    },
                ]
            },
        ]
    }


@router.route('GET', '/history_ui')
def _history(params):
    """查看 MOC 生成历史（重定向到 moc_list_ui 的逻辑）。"""
    return _moc_list(params)


def handle(request):
    return router.handle(request)
