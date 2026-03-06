"""
AI 分类器的通用基础逻辑 - 提供共享的 prompt 和解析逻辑
"""

import json
from ..base import CalendarEvent, Classification, AIClassifier


# 通用分类 prompt 模板
CLASSIFY_PROMPT = """你是一个日程分类助手。根据以下日程信息，返回 JSON 格式的分类和标签。

日程信息:
- 标题: {summary}
- 地点: {location}
- 组织者: {organizer}
- 参与者: {attendees}
- 描述: {description}

请分析日程性质，返回严格的 JSON（不要其他文字）:
{{
  "category": "从以下选一个: 客户拜访, 内部会议, 团队管理, 培训学习, 商务活动, 项目评审, 方案汇报, 聚餐社交",
  "tags": ["标签1", "标签2", "标签3"],
  "event_type": "从以下选一个: meeting, visit, review, training, social, report, other"
}}

分类规则:
- 标题/描述含"拜访""客户""谈参"→ 客户拜访
- 标题含"周会""例会""双周会""FT周会"→ 内部会议
- 标题含"晋级""晋升""反馈"→ 团队管理
- 标题含"培训""学习""分享""公开课"→ 培训学习
- 标题含"晚宴""春茗""晚餐""聚餐"→ 聚餐社交
- 标题含"评审""review"→ 项目评审
- 标题含"汇报""方案""专项"→ 方案汇报
- 其他商务相关 → 商务活动

标签规则（选2-4个最相关的）:
- 从内容提取关键主题词
- 标签应简洁，每个不超过4个字

event_type 用于选择笔记模板:
- meeting: 会议类（周会/例会/双周会）
- visit: 拜访类（客户拜访/商务拜访）
- review: 评审类（项目评审/晋升评审）
- training: 培训/学习/分享
- social: 社交/聚餐/活动
- report: 汇报/方案
- other: 其他"""


def build_prompt(event: CalendarEvent) -> str:
    """构建分类 prompt"""
    attendees_str = ", ".join(event.attendees[:10])
    desc = (event.description or "")[:500]
    return CLASSIFY_PROMPT.format(
        summary=event.summary,
        location=event.location,
        organizer=event.organizer,
        attendees=attendees_str,
        description=desc,
    )


def parse_ai_response(text: str) -> Classification:
    """解析 AI 返回的 JSON 文本"""
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    result = json.loads(text.strip())
    return Classification(
        category=result.get("category", "商务活动"),
        tags=result.get("tags", ["工作"]),
        event_type=result.get("event_type", "other"),
        confidence=0.8,
    )
