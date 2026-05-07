# 🗺️ MOC Knowledge Map — remio 知识地图 aApp

> 基于 remio 全知识库构建 **Map of Content (MOC)** 知识地图，提供主题地图可视化、跨域深度总结、自动知识发现。

<p align="center">
  <img src="https://img.shields.io/badge/remio-aApp-blue" alt="remio aApp" />
  <img src="https://img.shields.io/badge/runtime-embedded-green" alt="embedded runtime" />
  <img src="https://img.shields.io/badge/endpoints-14-orange" alt="14 endpoints" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT License" />
</p>

---

## 📖 目录

- [✨ 功能特性](#-功能特性)
- [🧠 核心概念](#-核心概念)
- [🏗️ 架构设计](#️-架构设计)
- [📁 文件结构](#-文件结构)
- [🚀 安装部署](#-安装部署)
- [🎮 使用指南](#-使用指南)
- [🔌 端点参考](#-端点参考)
- [⚙️ 配置说明](#️-配置说明)
- [🧩 与其他 aApp 的关系](#-与其他-aapp-的关系)
- [❓ 常见问题](#-常见问题)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

---

## ✨ 功能特性

### 🏗️ MOC 地图构建
选定一个**知识域**（Collection / 文件夹 / 搜索结果），AI 会自动分析其中所有笔记，生成结构化的知识地图：
- 识别**主题集群**（不是简单关键词分类，而是语义理解后的自然分组）
- 发现**笔记间关联**（引用、互补、因果关系）
- 检测**与域外的桥梁**（连接到其他知识域的概念）
- 评估**知识完整性**（识别缺口和值得深入的方向）

### 🌐 跨域深度总结
选择 2 个或更多知识域，AI 会合成跨域分析报告：
- **交汇点**：哪些话题在多个域同时出现
- **视角对比**：同一话题在不同域的差异化观点
- **管道连接**：一个域的输出是否是另一个域的输入（例：GPT Image 2 分镜 → Seedance 2.0 视频生成）
- **统一洞察**：只有结合多个域才能得出的新发现
- **弱信号**：只在一个域出现但值得全局关注的新趋势

### 🔍 知识发现
自动扫描最近新增的内容，发现隐藏的关联：
- 检测跨域**关键词共现**
- 发现语义相似但位于不同域的**潜在关联**
- 追踪**话题演进**轨迹
- 识别**新兴主题**和弱信号

### 📈 话题时间线
输入一个关键词，展示它在你的知识库中的讨论轨迹：
- 话题全景：涉及哪些方面
- 时间线：按时间排列关键讨论
- 跨域分布：在哪些域被讨论，各域视角有何不同
- 演进方向：话题未来可能如何发展

---

## 🧠 核心概念

### 什么是 MOC？
**Map of Content (MOC)** 是一种知识管理方法，通过为笔记集合创建"地图"来揭示知识之间的结构关系。不同于传统的文件夹分类，MOC 关注的是**笔记之间的关联**而非层级。

### 什么是"域"？
在本 aApp 中，"域"是 MOC 构建的输入范围，可以是：

| 域类型 | 说明 | 示例 |
|--------|------|------|
| `collection` | remio 中的合集 | "GPT Image 2 提示词"、"Seedance 2.0 提示词" |
| `folder` | 同步文件夹 | "微信群聊总结"、"Documents"、"Desktop" |
| `search` | 全库搜索结果 | 搜索 "Claude Code"、"AI 视频生成" |

### 数据流

```
┌──────────────────────────────────────────────────────────┐
│                    remio 知识库                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Collection│  │Collection│  │  Folder   │  │  Search  │ │
│  │  (合集)  │  │  (合集)  │  │ (文件夹)  │  │ (搜索)   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │       │
│       └──────────────┴──────┬───────┴──────────────┘       │
│                             │                              │
│                    search_notes / rag                       │
│                             │                              │
└─────────────────────────────┼──────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   MOC 知识地图引擎  │
                    │   (system.md + AI)  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  MOC 构建     │  │
                    │  ├───────────────┤  │
                    │  │  跨域总结     │  │
                    │  ├───────────────┤  │
                    │  │  知识发现     │  │
                    │  ├───────────────┤  │
                    │  │  话题时间线   │  │
                    │  └───────────────┘  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  生成结果 + 保存    │
                    │  ┌───────────────┐  │
                    │  │ remio Note    │  │
                    │  │ + Collection  │  │
                    │  │ + History     │  │
                    │  └───────────────┘  │
                    └────────────────────┘
```

---

## 🏗️ 架构设计

本 aApp 遵循 remio 的 **embedded runtime** 模式——所有操作由用户交互驱动，无后台服务。

### 设计原则
1. **知识消费层，不是生产层**：aApp 不替代已有的知识采集管道（如微信聊天自动摘要），而是在已采集的知识之上做发现和关联
2. **增量而非全量**：每次只处理用户选定的域，不会全库扫描
3. **AI 驱动**：核心分析能力来自 LLM，通过 `run_prompt` 调用
4. **保存即关联**：生成的 MOC 笔记自动关联到对应的 Collection

### 关键组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **manifest** | `manifest.json` | aApp 元信息、注册内容动作和快捷命令 |
| **API 定义** | `api.json` | 14 个端点的参数定义和描述 |
| **业务逻辑** | `logic.py` | 所有端点的 Python 实现 |
| **AI 引擎** | `system.md` | 3 套 prompt 模板（MOC / 跨域 / 发现） |
| **路由文档** | `SKILL.md` | Agent 如何发现和调用本 aApp |

---

## 📁 文件结构

```
moc-map/                      # aApp 根目录
├── manifest.json             # ID、名称、i18n、content action、shortcut
├── api.json                  # 14 个端点定义
├── logic.py                  # 完整业务逻辑（~47KB，600+ 行）
├── system.md                 # AI 分析引擎 prompt 模板
└── SKILL.md                  # Agent 路由和调用文档
```

### 依赖
本 aApp 使用 remio SDK 内置模块，**无需额外安装任何依赖**：

- `remio_sdk.router` — 端点路由
- `remio_sdk.run_prompt` — AI 分析调用
- `remio_sdk.search_notes` — 知识库搜索
- `remio_sdk.read_note` — 读取笔记内容
- `remio_sdk.create_note` — 创建笔记
- `remio_sdk.add_note_to_collection` — 关联合集
- `remio_sdk.get_state` / `set_state` — 历史记录持久化

---

## 🚀 安装部署

### 前提条件
- 已安装 [remio](https://remio.com) 桌面客户端
- remio 版本支持 aApp 功能

### 方式一：从源码安装（推荐开发者）

1. **克隆本仓库**
   ```bash
   git clone https://github.com/violin86318/moc-map-aapp.git
   cd moc-map-aapp
   ```

2. **复制到 remio aApps 开发目录**

   remio 的 aApps 开发目录通常位于：
   ```bash
   # macOS
   ~/Library/Application\ Support/remio/Users/<YOUR_USER_ID>/agent/remio/aapps-dev/moc-map/
   ```
   
   将 `moc-map/` 文件夹（包含 5 个文件）复制到上述路径的 `moc-map/` 子目录中：
   ```bash
   # 假设 REMIO_AGENT_DIR 是你的 remio agent 目录
   REMIO_AGENT_DIR="$HOME/Library/Application Support/remio/Users/<YOUR_USER_ID>/agent"
   
   mkdir -p "$REMIO_AGENT_DIR/remio/aapps-dev/moc-map"
   cp -r moc-map/ "$REMIO_AGENT_DIR/remio/aapps-dev/moc-map/moc-map/"
   ```

3. **在 remio 中部署**

   在 remio 对话中告诉 AI：
   > "使用 aapp-studio 部署 moc-map"

   或者手动将文件从 `aapps-dev/` 复制到 `aapps/` 目录。

### 方式二：通过 remio aApp 市场安装

> 🚧 发布到市场后可用。目前请使用方式一。

在 remio 中搜索 "moc-map" 或 "知识地图" 即可一键安装。

### 验证安装

安装后，在 remio 对话中输入：
> "打开 MOC 知识地图"

如果看到知识全景首页 UI，说明安装成功。

---

## 🎮 使用指南

### 入口 1：对话触发

在 remio 对话中直接说：
```
打开 MOC 知识地图
```
或
```
打开知识地图
```

### 入口 2：快捷命令

在对话中输入：
```
<<moc 提示词工程
```
会自动搜索 "提示词工程" 相关笔记并构建 MOC。

### 入口 3：内容动作

在任意笔记上，通过右键菜单选择 **「🗺️ 加入知识地图」**，会以该笔记标题为关键词搜索相关笔记并构建 MOC。

---

### 场景一：为一个合集构建 MOC

**目标**：你想了解 "GPT Image 2 提示词" 合集中的知识结构。

1. 打开 MOC 知识地图 → 点击 **"📚 GPT Image 2 提示词"**
2. 查看域内笔记列表（标题、类型、所属合集）
3. 点击 **"🏗️ 为此域构建 MOC"**
4. 等待 AI 分析（约 30 秒）
5. 查看生成的知识地图，包含：
   - 📊 全景概览
   - 🎯 主题地图（按热度排列的主题集群）
   - 🔗 跨域桥梁（与其他合集的关联）
   - 📭 知识缺口
   - 💡 探索建议
6. 点击 **"📝 保存为笔记"** 保存到 remio

### 场景二：跨域分析

**目标**：你想了解 "GPT Image 2" 和 "Seedance 2.0" 之间的知识关联。

1. 打开 MOC 知识地图 → 点击 **"🌐 跨域深度总结"**
2. 选择多个合集（如 "GPT Image 2 提示词" + "Seedance 2.0 提示词"）
3. AI 会发现：
   - 🔥 **交汇点**：哪些话题在两个合集同时出现
   - 🔄 **管道连接**：GPT Image 2 的分镜输出 → Seedance 2.0 的视频输入
   - 🌱 **弱信号**：只在一个合集出现但值得关注的新趋势
   - 🎯 **行动建议**：下一步应该创建什么内容

### 场景三：知识发现

**目标**：你想看看最近一周知识库有什么新动态。

1. 打开 MOC 知识地图 → 点击 **"🔍 知识发现"**
2. AI 会扫描最近 7 天新增的所有内容
3. 自动生成发现报告：
   - 🆕 新发现的跨域关联
   - 📈 话题演进趋势
   - 🌱 新兴主题

### 场景四：话题追踪

**目标**：你想追踪 "Claude Code" 在知识库中的讨论轨迹。

1. 打开 MOC 知识地图 → 点击 **"📈 话题时间线"**
2. 输入关键词 "Claude Code"
3. AI 会展示：
   - 话题全景（涉及哪些方面）
   - 时间线（按时间排列的讨论）
   - 跨域分布（在微信群聊、技术文档、笔记中各有什么视角）
   - 演进方向

### 场景五：从单条笔记出发

**目标**：你在看某条笔记，想了解它与知识库中其他内容的关联。

1. 在笔记上右键 → 选择 **"🗺️ 加入知识地图"**
2. aApp 会以该笔记标题为关键词搜索全库
3. 自动构建围绕这条笔记的 MOC 知识地图

---

## 🔌 端点参考

### UI 端点（14 个）

| 方法 | 路径 | 说明 | 关键参数 |
|------|------|------|----------|
| `GET` | `/` | 🏠 知识全景首页 | — |
| `POST` | `/domain_map_ui` | 📍 域内主题分布 | `domain_type`, `domain_id`, `domain_name` |
| `POST` | `/build_moc_ui` | 🏗️ 构建 MOC | `domain_type`, `domain_name`, `query`, `depth` |
| `POST` | `/build_moc_from_note_ui` | 🗺️ 从笔记构建 | `note_id`, `note_title` |
| `POST` | `/build_moc_shortcut` | ⚡ 快捷命令 | `input` |
| `POST` | `/cross_summary_ui` | 🌐 跨域总结 | `domains[]`, `topic` |
| `POST` | `/discover_ui` | 🔍 知识发现 | `time_range`, `scope` |
| `POST` | `/topic_timeline_ui` | 📈 话题时间线 | `topic` |
| `GET` | `/moc_list_ui` | 📑 MOC 列表 | — |
| `POST` | `/save_moc_ui` | 💾 保存笔记 | `history_id`, `collection_name` |
| `GET` | `/history_ui` | 📋 全部历史 | — |
| `POST` | `/detail_ui` | 📄 历史详情 | `history_id` |
| `POST` | `/delete_ui` | 🗑️ 删除历史 | `history_id` |
| `GET` | `/_menu` | 📋 动态菜单 | — |

### 参数详情

#### `domain_type` — 域类型
| 值 | 说明 |
|----|------|
| `collection` | remio 合集（按名称匹配） |
| `folder` | 同步文件夹（按文件夹别名） |
| `search` | 全库搜索（按 query 关键词） |

#### `depth` — 分析深度
| 值 | 说明 | 笔记读取量 |
|----|------|------------|
| `overview` | 概览级别，重点列出主题和关联 | 少 |
| `standard` | 标准级别（默认），包含跨域桥梁和缺口 | 中 |
| `deep` | 深度分析，详细分析每条笔记内容 | 多 |

#### `time_range` — 时间范围
| 值 | 说明 |
|----|------|
| `last_week` | 最近 7 天（默认） |
| `last_month` | 最近 30 天 |

---

## ⚙️ 配置说明

### 可自定义的文件夹映射

在 `logic.py` 中有一个 `KNOWN_FOLDERS` 字典，用于将用户友好的名称映射到实际文件路径。你可以根据自己的 remio 同步文件夹配置进行修改：

```python
KNOWN_FOLDERS = {
    'Clipping-微信群聊': '/path/to/your/Clipping/微信群聊总结',
    'Documents': '/path/to/Documents',
    'Desktop': '/path/to/Desktop',
    'Downloads': '/path/to/Downloads',
}
```

### System Prompt 自定义

`system.md` 文件定义了 AI 分析引擎的行为。你可以修改它来调整：
- 输出格式（Markdown 模板）
- 分析重点（例如更关注某个领域）
- 语言风格
- 规则和限制

### 历史记录

所有生成结果保存在 remio 的 state 存储中（`moc_history` key），最多保留 100 条。每条记录包含：
- 生成标题和类型
- 来源域信息
- 源笔记列表
- AI 生成的完整文本
- 是否已保存为 remio note

---

## 🧩 与其他 aApp 的关系

### 发芽笔记 (sprout-notes)
- **发芽笔记**：从**单条笔记**发散洞察（深度方向）
- **MOC 知识地图**：从**笔记集合**发现关联（广度方向）
- **推荐工作流**：先用 MOC 地图发现关联 → 再用发芽笔记深入挖掘某条笔记

### 微信聊天摘要管道
- 微信聊天摘要管道（Claude Code skill + Gemini）自动运行，负责**知识采集**
- MOC 知识地图是**知识消费层**，不会干扰采集管道
- 两者通过 remio 知识库自然对接

---

## ❓ 常见问题

### Q: 构建一个 MOC 需要多长时间？
A: 通常 30-60 秒，取决于笔记数量和分析深度。`overview` 最快，`deep` 最慢。

### Q: 支持哪些语言的笔记？
A: 支持所有语言。AI 引擎会根据笔记内容自动适应。UI 界面支持中文、英文、日文。

### Q: 生成的 MOC 会自动更新吗？
A: 目前不会自动更新。你需要手动重新构建。每次构建会作为新的历史记录保存。

### Q: 数据会离开本地吗？
A: 本 aApp 运行在 remio 的 embedded runtime 中，所有数据处理都在本地完成。AI 分析通过 remio 的 `run_prompt` 接口调用，数据流向与你在 remio 中正常对话一致。

### Q: 支持多少条笔记？
A: 单次 MOC 构建建议不超过 40 条笔记（受 AI 上下文窗口限制）。如果域内笔记过多，可以通过 `query` 参数缩小范围。

### Q: 可以同时选多个合集吗？
A: 可以，使用"跨域深度总结"功能，选择 2 个或更多的合集进行分析。

---

## 🛣️ 路线图

- [ ] **自动增量更新**：检测已有 MOC 的源域变化，提示用户更新
- [ ] **可视化地图**：生成交互式知识图谱 SVG（节点 + 连线）
- [ ] **MOC 嵌套**：支持 MOC 内引用其他 MOC（多层知识地图）
- [ ] **定时知识发现**：通过 scheduler aApp 定期运行知识发现扫描
- [ ] **导出格式**：支持导出为 Mermaid 图、OPML 等格式
- [ ] **多语言 UI 完善**：英文和日文界面的完整翻译

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交修改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发调试

修改文件后，在 remio 对话中说"使用 aapp-studio 重新部署 moc-map"即可热更新。

---

## 📄 许可证

[MIT License](LICENSE)

---

<p align="center">
  Made with ❤️ for <a href="https://remio.com">remio</a> · by <a href="https://github.com/violin86318">violin</a>
</p>
