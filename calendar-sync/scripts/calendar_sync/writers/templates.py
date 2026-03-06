"""
Markdown 内容模板 - 所有笔记输出插件共享

根据事件类型生成对应的 Markdown 模板内容。
"""

from ..base import CalendarEvent


def build_event_info(event: CalendarEvent) -> str:
    """构建事件基本信息区块"""
    parts = []
    if event.start_time:
        time_str = event.start_time.strftime("%Y-%m-%d %H:%M")
        if event.end_time:
            time_str += f" ~ {event.end_time.strftime('%H:%M')}"
        parts.append(f"🕐 时间: {time_str}")
    if event.location:
        parts.append(f"📍 地点: {event.location}")
    if event.organizer:
        parts.append(f"👤 组织者: {event.organizer}")
    if event.attendees:
        att_str = ", ".join(event.attendees[:15])
        if len(event.attendees) > 15:
            att_str += f" 等{len(event.attendees)}人"
        parts.append(f"👥 参与者: {att_str}")
    return "\n".join(parts)


def build_template(event: CalendarEvent, event_type: str, source_name: str = "日历") -> str:
    """根据事件类型构建 Markdown 模板"""
    info = build_event_info(event)
    sections = []

    if info:
        sections.append(f"> 📅 {info.replace(chr(10), chr(10) + '> ')}\n")

    templates = {
        "meeting": [
            ("## 会议议题", "- [ ] 议题1\n- [ ] 议题2"),
            ("## 会议纪要", ""),
            ("## 待办事项", "- [ ] "),
        ],
        "visit": [
            ("## 拜访目的", ""),
            ("## 沟通要点", "- [ ] 要点1\n- [ ] 要点2"),
            ("## 客户反馈", ""),
            ("## 后续跟进", "- [ ] "),
        ],
        "review": [
            ("## 评审内容", ""),
            ("## 关键结论", ""),
            ("## 后续行动", "- [ ] "),
        ],
        "training": [
            ("## 学习主题", ""),
            ("## 核心收获", "- [ ] 收获1\n- [ ] 收获2"),
            ("## 实践计划", "- [ ] "),
        ],
        "social": [
            ("## 活动记录", ""),
        ],
        "report": [
            ("## 汇报主题", ""),
            ("## 核心内容", ""),
            ("## 决策结论", ""),
            ("## 后续跟进", "- [ ] "),
        ],
        "other": [
            ("## 详情", ""),
            ("## 笔记", ""),
        ],
    }

    template_sections = templates.get(event_type, templates["other"])
    for heading, content in template_sections:
        sections.append(heading)
        if content:
            sections.append(content)
        sections.append("")

    if event.description:
        sections.append("---")
        sections.append("### 原始描述")
        sections.append(event.description)
        sections.append("")

    sections.append(f"*— 自动同步自{source_name}*")
    return "\n".join(sections)
