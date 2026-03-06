"""
关键词规则分类器 - 无需 AI，基于关键词匹配
"""

from ..base import AIClassifier, CalendarEvent, Classification
from ..registry import PluginRegistry


class KeywordClassifier(AIClassifier):
    """基于关键词规则的分类器（不需要 AI API）"""

    def __init__(self, config: dict = None):
        self.config = config or {}

    @property
    def name(self) -> str:
        return "关键词规则"

    def classify(self, event: CalendarEvent) -> Classification:
        summary = event.summary or ""
        desc = event.description or ""
        text = summary + " " + desc

        rules = [
            (["拜访", "谈参", "客户"], "客户拜访", ["工作", "业务", "拜访"], "visit"),
            (["周会", "例会", "双周会", "FT周会"], "内部会议", ["工作", "会议"], "meeting"),
            (["晋级", "晋升", "反馈"], "团队管理", ["工作", "管理"], "review"),
            (["培训", "学习", "分享", "公开课"], "培训学习", ["工作", "培训"], "training"),
            (["晚宴", "春茗", "晚餐", "聚餐"], "聚餐社交", ["工作", "社交"], "social"),
            (["评审", "review"], "项目评审", ["工作", "评审"], "review"),
            (["汇报", "方案", "专项"], "方案汇报", ["工作", "汇报"], "report"),
        ]

        for keywords, category, tags, event_type in rules:
            if any(kw in text for kw in keywords):
                return Classification(
                    category=category,
                    tags=tags,
                    event_type=event_type,
                    confidence=0.6,
                )

        return Classification(
            category="商务活动",
            tags=["工作", "业务"],
            event_type="other",
            confidence=0.3,
        )


PluginRegistry.register_classifier("keyword", KeywordClassifier)
