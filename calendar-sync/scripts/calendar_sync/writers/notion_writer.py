"""
Notion 笔记输出插件
"""

import time

from ..base import NoteWriter, CalendarEvent, Classification
from ..registry import PluginRegistry


def _retry(func, max_retries=4, base_delay=3):
    """通用重试装饰器，处理网络不稳定"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                time.sleep(delay)
            else:
                raise


class NotionWriter(NoteWriter):
    """Notion 数据库笔记输出"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.token = config.get("token", "")
        self.database_id = config.get("database_id", "")
        self.domain_field = config.get("domain_field", "领域")
        self.category_field = config.get("category_field", "分类")
        self.tags_field = config.get("tags_field", "标签")
        self.date_field = config.get("date_field", "Date")
        self.default_domain = config.get("default_domain", "🏢工作")
        self._client = None

    @property
    def name(self) -> str:
        return "Notion"

    def validate_config(self) -> list[str]:
        missing = []
        if not self.token:
            missing.append("output.token (NOTION_TOKEN)")
        if not self.database_id:
            missing.append("output.database_id (NOTION_DATABASE_ID)")
        return missing

    def _get_client(self):
        if not self._client:
            from notion_client import Client as NotionClient
            self._client = NotionClient(auth=self.token)
        return self._client

    def _check_duplicate(self, event: CalendarEvent) -> str | None:
        """检查 Notion 数据库中是否已存在同标题+同日期的条目，返回已有页面 URL 或 None
        如果网络异常则抛出异常，避免误创建重复条目。
        """
        client = self._get_client()

        filter_conditions = {
            "property": "title",
            "title": {"equals": event.summary},
        }

        # 不吞掉异常：网络失败时必须抛出，否则会误判为"无重复"导致重复创建
        resp = _retry(lambda: client.databases.query(
            database_id=self.database_id,
            filter=filter_conditions,
            page_size=10,
        ))

        if not resp.get("results"):
            return None

        for page in resp["results"]:
            date_prop = page.get("properties", {}).get(self.date_field, {})
            if date_prop and date_prop.get("date"):
                existing_start = date_prop["date"].get("start", "")
                if event.start_time and existing_start:
                    existing_date = existing_start[:10]
                    event_date = event.start_time.strftime("%Y-%m-%d")
                    if existing_date == event_date:
                        return page.get("url", "已存在")
            elif not event.start_time:
                return page.get("url", "已存在")

        return None

    def write(self, event: CalendarEvent, classification: Classification) -> str:
        client = self._get_client()

        # 服务端去重
        existing_url = self._check_duplicate(event)
        if existing_url:
            return f"SKIP_DUP:{existing_url}"

        # 构建属性
        date_prop = {}
        if event.start_time:
            date_prop["start"] = event.start_time.isoformat()
            if event.end_time and event.end_time != event.start_time:
                date_prop["end"] = event.end_time.isoformat()

        tag_names = list(classification.tags)
        if "周报" not in tag_names:
            tag_names.append("周报")

        properties = {
            "title": {"title": [{"text": {"content": event.summary}}]},
            self.domain_field: {"select": {"name": self.default_domain}},
            self.tags_field: {"multi_select": [{"name": t} for t in tag_names]},
            self.category_field: {"multi_select": [{"name": classification.category}]},
        }
        if date_prop:
            properties[self.date_field] = {"date": date_prop}

        # 构建内容块
        children = self._build_blocks(event, classification)

        response = _retry(lambda: client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
            children=children,
        ))

        return response.get("url", "")

    def _build_blocks(self, event: CalendarEvent, classification: Classification) -> list[dict]:
        """构建 Notion block 内容"""
        blocks = []
        event_type = classification.event_type

        # 事件信息 callout
        info = self._build_event_info(event)
        if info:
            blocks.append(info)

        # 根据事件类型构建模板
        template_map = {
            "meeting": self._meeting_blocks,
            "visit": self._visit_blocks,
            "review": self._review_blocks,
            "training": self._training_blocks,
            "social": self._social_blocks,
            "report": self._report_blocks,
        }

        builder = template_map.get(event_type, self._default_blocks)
        blocks.extend(builder(event))

        # 原始描述
        if event.description:
            blocks.append(self._divider())
            blocks.append(self._heading("原始描述", 3))
            blocks.extend(self._desc_blocks(event.description))

        blocks.append(self._paragraph(f"— 自动同步自{event.source or '日历'}", italic=True, color="gray"))
        return blocks

    # === Notion block 构建工具 ===

    def _heading(self, text, level=2):
        return {
            "object": "block", "type": f"heading_{level}",
            f"heading_{level}": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _paragraph(self, text, **annotations):
        rt = {"type": "text", "text": {"content": text}}
        if annotations:
            rt["annotations"] = annotations
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [rt]}}

    def _callout(self, text, emoji="📅"):
        return {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
            },
        }

    def _todo(self, text, checked=False):
        return {
            "object": "block", "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "checked": checked,
            },
        }

    def _divider(self):
        return {"object": "block", "type": "divider", "divider": {}}

    def _desc_blocks(self, description):
        blocks = []
        desc = description.replace("\\r", "\r").replace("\\n", "\n")
        while desc:
            blocks.append(self._paragraph(desc[:2000]))
            desc = desc[2000:]
        return blocks

    def _build_event_info(self, event: CalendarEvent):
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
        return self._callout("\n".join(parts), "📅") if parts else None

    # === 模板构建器 ===

    def _meeting_blocks(self, event):
        return [
            self._heading("会议议题"), self._todo("议题1"), self._todo("议题2"),
            self._divider(),
            self._heading("会议纪要"), self._paragraph(""),
            self._divider(),
            self._heading("待办事项"), self._todo(""),
        ]

    def _visit_blocks(self, event):
        return [
            self._heading("拜访目的"), self._paragraph(""),
            self._divider(),
            self._heading("沟通要点"), self._todo("要点1"), self._todo("要点2"),
            self._divider(),
            self._heading("客户反馈"), self._paragraph(""),
            self._divider(),
            self._heading("后续跟进"), self._todo(""),
        ]

    def _review_blocks(self, event):
        return [
            self._heading("评审内容"), self._paragraph(""),
            self._divider(),
            self._heading("关键结论"), self._paragraph(""),
            self._divider(),
            self._heading("后续行动"), self._todo(""),
        ]

    def _training_blocks(self, event):
        return [
            self._heading("学习主题"), self._paragraph(""),
            self._divider(),
            self._heading("核心收获"), self._todo("收获1"), self._todo("收获2"),
            self._divider(),
            self._heading("实践计划"), self._todo(""),
        ]

    def _social_blocks(self, event):
        return [
            self._heading("活动记录"), self._paragraph(""),
        ]

    def _report_blocks(self, event):
        return [
            self._heading("汇报主题"), self._paragraph(""),
            self._divider(),
            self._heading("核心内容"), self._paragraph(""),
            self._divider(),
            self._heading("决策结论"), self._paragraph(""),
            self._divider(),
            self._heading("后续跟进"), self._todo(""),
        ]

    def _default_blocks(self, event):
        return [
            self._heading("详情"), self._paragraph(""),
            self._divider(),
            self._heading("笔记"), self._paragraph(""),
        ]


PluginRegistry.register_writer("notion", NotionWriter)
