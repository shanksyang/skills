---
name: calendar-sync
description: "通用日历同步工具。This skill should be used when users need to sync calendar events to note-taking apps, set up calendar sync pipelines, classify events with AI, or integrate CalDAV/Google/Outlook calendars with Notion/Obsidian/Logseq. Covers multi-source calendar sync, AI-powered event classification, multi-target note creation with structured templates."
---

# 通用日历同步工具

插件化架构的日历同步引擎，支持多种日历源、AI 模型和笔记应用的灵活组合。

## 概述

核心工作流：日历源 → AI 智能分类 → 笔记应用

```
日历源 (CalDAV/Google/Outlook/iCal)
       ↓
  calendar_sync_cli.py（同步引擎）
       ↓
  AI 分类 (智谱/OpenAI/Claude/Ollama/关键词)
       ↓
  笔记应用 (Notion/Obsidian/Logseq/Markdown)
```

### 支持的插件

| 层级 | 可选项 | 配置键 |
|------|--------|--------|
| 日历源 | CalDAV (企微/iCloud/Nextcloud)、Google Calendar、Outlook/365、iCal 文件/URL | `source.type` |
| AI 分类 | 智谱 AI、OpenAI（含 DeepSeek 等兼容接口）、Claude、Ollama 本地模型、关键词规则 | `ai.type` |
| 笔记输出 | Notion、Obsidian、Logseq、通用 Markdown | `output.type` |

## 使用场景

- 用户需要将日历事件同步到笔记应用（任意组合）
- 用户提到"日历同步"、"CalDAV"、"日程同步"、"Google Calendar"、"Outlook 日历"
- 用户希望自动分类会议/事件笔记
- 用户需要将企业微信/Google/Outlook 日历与 Notion/Obsidian/Logseq 集成
- 用户想用 AI 对日程进行智能分类

## 脚本

### `scripts/calendar_sync_cli.py`

主 CLI 入口，可直接执行。

**命令：**
```bash
# 列出可用插件
python3 scripts/calendar_sync_cli.py --list-plugins

# 验证配置
python3 scripts/calendar_sync_cli.py --validate

# 列出所有日历
python3 scripts/calendar_sync_cli.py --list-calendars

# 测试模式：读取 + AI 分类，不写入笔记
python3 scripts/calendar_sync_cli.py --test --days-back 7 --days-forward 7

# 完整同步
python3 scripts/calendar_sync_cli.py --days-back 7 --days-forward 30

# 指定配置文件
python3 scripts/calendar_sync_cli.py --config my_config.yaml

# 仅同步指定日历
python3 scripts/calendar_sync_cli.py --calendar "shanksyang的日历"
```

**核心特性：**
- 通过 `sync_state.json` 基于 UID 去重（可安全重复执行）
- AI 智能分类为 8 个类别，AI 不可用时自动降级为关键词规则
- 根据事件类型自动选择 6 种内容模板
- 通过 YAML 配置文件灵活组合插件
- 支持 `${ENV_VAR}` 语法引用环境变量

### `scripts/setup_calendar_sync.sh`

项目初始化脚本：
```bash
bash scripts/setup_calendar_sync.sh /path/to/new/project
```

创建：核心模块、配置模板、`.env.example`、`requirements.txt`、`.gitignore`。

## 参考文档

### `references/environment_setup.md`

帮助用户配置环境变量、安装依赖或排查连接问题时阅读。包含：
- YAML 配置文件和 .env 两种配置方式
- 各日历源、AI 模型、笔记应用的凭据获取方式
- Python 依赖版本说明
- 验证命令

### `references/plugin_architecture.md`

理解架构或扩展新插件时阅读。包含：
- 三层插件架构说明
- 所有内置插件列表
- 统一数据结构（CalendarEvent、Classification）
- 扩展新插件的代码示例

### `references/notion_database_schema.md`

使用 Notion 输出时阅读。包含：
- 数据库属性 Schema
- 字段名自定义方法
- 分类 → 模板映射表

## 资源文件

### `assets/config/calendar_sync.example.yaml`

完整的配置文件模板，包含所有插件的配置示例。复制到项目根目录使用。

### `assets/config/category_rules.yaml`

分类规则配置，含置信度评分。

## 工作流：搭建新项目

1. 运行 `scripts/setup_calendar_sync.sh` 初始化项目结构
2. 阅读 `references/environment_setup.md` 了解配置说明
3. 编辑 `calendar_sync.yaml` 选择日历源、AI 模型和笔记输出
4. 在 `.env` 中填写凭据
5. `pip install -r requirements.txt` 安装依赖
6. `python3 calendar_sync_cli.py --validate` 验证配置
7. `python3 calendar_sync_cli.py --list-calendars` 测试连接
8. `python3 calendar_sync_cli.py --test` 测试读取+分类
9. `python3 calendar_sync_cli.py` 正式同步

## 工作流：常见组合配置

### 企业微信 + 智谱 AI + Notion（经典组合）
```yaml
source: { type: caldav, preset: wecom, username: ${WECOM_CALDAV_USERNAME}, password: ${WECOM_CALDAV_PASSWORD} }
ai: { type: zhipu, api_key: ${ZHIPU_API_KEY} }
output: { type: notion, token: ${NOTION_TOKEN}, database_id: ${NOTION_DATABASE_ID} }
```

### Google Calendar + OpenAI + Obsidian
```yaml
source: { type: google, credentials_file: credentials.json }
ai: { type: openai, api_key: ${OPENAI_API_KEY}, model: gpt-4o-mini }
output: { type: obsidian, vault_path: /path/to/vault, folder: Calendar }
```

### iCal 订阅 + Ollama 本地 + Logseq
```yaml
source: { type: ical, urls: ["https://example.com/feed.ics"] }
ai: { type: ollama, model: qwen2.5:7b }
output: { type: logseq, graph_path: /path/to/graph, journal: true }
```

### Outlook + 关键词规则 + Markdown
```yaml
source: { type: outlook, client_id: your-app-id }
ai: { type: keyword }
output: { type: markdown, output_dir: ./notes, organize_by: date }
```

## 工作流：问题排查

| 问题 | 解决方案 |
|------|----------|
| CalDAV 403 Forbidden | URL 末尾必须有 `/calendar/`，密码可能已过期 |
| Notion API 报错 | 确保使用 `notion-client==2.2.1`，检查 Token 权限 |
| AI 分类降级 | 正常现象，关键词规则仍可提供不错的准确率 |
| 重复条目 | 基于 `sync_state.json` 的 UID 去重，删除该文件可重新同步 |
| Google 授权失败 | 检查 `credentials.json`，删除 `token.json` 重新授权 |
| 插件未找到 | 运行 `--list-plugins` 确认可用插件，检查配置中的 type 值 |

## 关键技术细节

- **Notion API**：必须使用 `notion-client==2.2.1`（v3 有不兼容变更）
- **CalDAV 企微端点**：`https://caldav.wecom.work/calendar/`，末尾 `/calendar/` 不可省略
- **配置优先级**：`--config` 参数 > `calendar_sync.yaml` > `config/calendar_sync.yaml` > `.env` 降级
- **AI 降级机制**：所有 AI 分类器在失败时自动降级为关键词规则分类
- **OpenAI 兼容接口**：通过 `base_url` 支持 DeepSeek、通义千问等兼容 API
