"""
通用日历同步工具 - 插件化架构

支持多种日历源、AI 模型和笔记应用的通用日历同步引擎。

架构:
    日历源 (CalendarSource) → 同步引擎 (SyncEngine) → AI 分类 (AIClassifier) → 笔记输出 (NoteWriter)

内置插件:
    日历源: CalDAV (企业微信/通用)、Google Calendar、Outlook/Exchange
    AI 分类: 智谱 AI、OpenAI、Claude、Ollama
    笔记输出: Notion、Obsidian、Logseq
"""

__version__ = "2.0.0"
