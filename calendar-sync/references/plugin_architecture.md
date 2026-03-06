# 插件架构说明

## 概述

通用日历同步工具采用三层插件架构：

```
日历源 (CalendarSource) → AI 分类 (AIClassifier) → 笔记输出 (NoteWriter)
```

每层都是可替换的，通过配置文件选择具体实现。

## 内置插件

### 日历源 (source.type)

| 类型 | 说明 | 依赖 |
|------|------|------|
| `caldav` | CalDAV 协议（企业微信/iCloud/Nextcloud 等） | caldav, icalendar |
| `google` | Google Calendar API | google-api-python-client |
| `outlook` | Outlook / Microsoft 365 (Graph API) | msal, requests |
| `ical` | iCalendar 文件或订阅 URL | icalendar |

#### CalDAV 预设

| preset | 服务 | URL |
|--------|------|-----|
| `wecom` | 企业微信 | `https://caldav.wecom.work/calendar/` |
| `icloud` | iCloud | `https://caldav.icloud.com/` |
| `nextcloud` | Nextcloud | `{server}/remote.php/dav/calendars/{username}/` |
| `synology` | Synology | `{server}/caldav/{username}/` |

### AI 分类器 (ai.type)

| 类型 | 说明 | 依赖 |
|------|------|------|
| `keyword` | 关键词规则匹配（无需 AI） | 无 |
| `zhipu` | 智谱 AI (GLM) | zhipuai |
| `openai` | OpenAI / 兼容接口 | openai |
| `claude` | Anthropic Claude | anthropic |
| `ollama` | Ollama 本地模型 | requests |

### 笔记输出 (output.type)

| 类型 | 说明 | 依赖 |
|------|------|------|
| `notion` | Notion 数据库 | notion-client==2.2.1 |
| `obsidian` | Obsidian Vault (Markdown) | 无 |
| `logseq` | Logseq 图谱 (大纲 Markdown) | 无 |
| `markdown` | 通用 Markdown 文件输出 | 无 |

## 数据流

```python
# 统一的事件数据结构
CalendarEvent:
    uid: str            # 唯一标识
    summary: str        # 标题
    description: str    # 描述
    location: str       # 地点
    start_time: datetime
    end_time: datetime
    attendees: list[str]
    organizer: str
    source: str         # 来源标识

# 分类结果
Classification:
    category: str       # 分类名称
    tags: list[str]     # 标签列表
    event_type: str     # meeting/visit/review/training/social/report/other
    confidence: float   # 置信度
```

## 扩展新插件

### 添加新的日历源

```python
# calendar_sync/sources/my_source.py
from calendar_sync.base import CalendarSource, CalendarEvent
from calendar_sync.registry import PluginRegistry

class MySource(CalendarSource):
    def __init__(self, config: dict):
        self.config = config

    @property
    def name(self) -> str:
        return "My Source"

    def connect(self): ...
    def list_calendars(self) -> list[dict]: ...
    def fetch_events(self, calendar_id, start, end) -> list[CalendarEvent]: ...

PluginRegistry.register_source("my_source", MySource)
```

### 添加新的 AI 分类器

```python
from calendar_sync.base import AIClassifier, CalendarEvent, Classification
from calendar_sync.registry import PluginRegistry

class MyClassifier(AIClassifier):
    @property
    def name(self) -> str:
        return "My Classifier"

    def classify(self, event: CalendarEvent) -> Classification: ...

PluginRegistry.register_classifier("my_classifier", MyClassifier)
```

### 添加新的笔记输出

```python
from calendar_sync.base import NoteWriter, CalendarEvent, Classification
from calendar_sync.registry import PluginRegistry

class MyWriter(NoteWriter):
    @property
    def name(self) -> str:
        return "My Writer"

    def write(self, event: CalendarEvent, classification: Classification) -> str: ...

PluginRegistry.register_writer("my_writer", MyWriter)
```
