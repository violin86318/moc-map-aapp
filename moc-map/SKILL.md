---
name: moc-map
description: "基于 remio 全知识库构建 M.O.C 知识地图，提供主题地图可视化、跨域深度总结、自动知识发现。支持 Collection、Folder、搜索结果集作为输入域。"
---

激活时调用 `GET /` (aapp_id: `moc-map`) 显示知识全景首页。

运行时: `embedded`

## 核心概念

- **域 (Domain)**: MOC 的输入范围，可以是 Collection、同步文件夹、或关键词搜索结果
- **MOC 地图**: 结构化的知识地图，包含主题集群、跨域桥梁、知识缺口
- **跨域总结**: 两个或多个域之间的 AI 合成分析
- **知识发现**: 自动扫描新增内容，发现隐藏关联

## Endpoints

### `GET /` [UI]
知识全景首页。展示所有 Collection、同步文件夹概览、快捷操作入口。

### `POST /domain_map_ui` [UI]
展示选定域内的笔记列表和主题分布预览。
- `domain_type` (required): `collection` | `folder` | `search`
- `domain_id` (optional): Collection 名称或文件夹路径
- `domain_name` (required): 域名称（用于展示）
- `query` (optional): 搜索型域的查询词

### `POST /build_moc_ui` [UI]
构建 MOC 知识地图。分析指定域的笔记，通过 `run_prompt` 生成结构化知识地图，自动保存为 remio 笔记。
- `domain_type` (required): `collection` | `folder` | `search`
- `domain_id` (optional): Collection 名称或文件夹路径
- `domain_name` (required): 域名称
- `query` (optional): 搜索关键词
- `depth` (optional): `overview` | `standard` | `deep`，默认 `standard`
- `include_external` (optional): boolean，是否发现域外关联，默认 true

如果 `domain_name` 为空，显示表单让用户填写。

### `POST /build_moc_from_note_ui` [UI]
从内容动作扩展触发。基于当前笔记所在的 Collection 或笔记标题构建 MOC。

### `POST /build_moc_shortcut` [UI]
从 `<<moc` 快捷命令触发。输入文本作为搜索关键词构建 MOC。

### `POST /cross_summary_ui` [UI]
跨域深度总结。选定 2+ 个域，AI 合成跨域分析报告。
- `domains` (required): 域列表，数组或逗号分隔字符串
- `topic` (optional): 聚焦主题
- `time_range` (optional): `last_week` | `last_month`

如果 `domains` 为空，显示表单。

### `POST /discover_ui` [UI]
知识发现。扫描最近新增内容，自动发现跨域关联和弱信号。
- `time_range` (optional): `last_week` | `last_month`
- `scope` (optional): `all` | `collections` | `folder`

### `POST /topic_timeline_ui` [UI]
话题时间线。输入关键词，展示话题在不同域的讨论轨迹。
- `topic` (required): 话题关键词
- `domains` (optional): 限定搜索的域列表，参见 api.json

### `GET /history_ui` [UI]
查看 MOC 生成历史（等同于 moc_list_ui）。

### `GET /moc_list_ui` [UI]
我的 MOC 历史。列出所有已生成的 MOC 记录。

### `POST /detail_ui` [UI]
查看一条 MOC 历史的完整内容。
- `history_id` (required)

### `POST /save_moc_ui` [UI]
将 MOC 结果保存为 remio 笔记（如果之前自动保存失败）。
- `history_id` (required)
- `collection_name` (optional): 关联到的 Collection 名称

### `POST /delete_ui` [UI]
删除一条 MOC 历史记录。
- `history_id` (required)

### `GET /_menu` [UI]
动态菜单。显示所有核心操作的快捷入口。

## 数据存储

- **生成历史**: 使用 aApp state (`moc_history`)，最多保留 100 条
- **MOC 笔记**: 自动保存为 remio 笔记，标题格式 `🗺️ [域名称] 知识地图`
- **System Prompt**: `system.md`，定义 MOC 引擎的分析框架和输出格式

## 内容动作扩展

在任意笔记上可触发「🗺️ 加入知识地图」，基于笔记所属 Collection 构建该域的 MOC。

## 快捷命令

`<<moc [关键词]` — 快速构建以关键词为搜索范围的 MOC。

## User Interactions

- 打开 MOC 知识地图 → `GET /`
- 查看 Collection 地图 → `POST /domain_map_ui` (domain_type=collection, domain_name=Collection名)
- 查看 文件夹地图 → `POST /domain_map_ui` (domain_type=folder, domain_id=路径, domain_name=名)
- 构建 MOC → `POST /build_moc_ui` (指定域)
- 跨域总结 → `POST /cross_summary_ui` (指定多个域)
- 知识发现 → `POST /discover_ui` (time_range=last_week)
- 话题时间线 → `POST /topic_timeline_ui` (topic=关键词)
- 查看 MOC 历史 → `GET /moc_list_ui`
