"""
通用 Markdown 文件输出插件 - 输出到任意目录
"""

from datetime import datetime
from pathlib import Path

from ..base import NoteWriter, CalendarEvent, Classification
from ..registry import PluginRegistry
from .templates import build_template


class MarkdownWriter(NoteWriter):
    """通用 Markdown 文件输出（适用于任何 Markdown 编辑器）"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.output_dir = config.get("output_dir", "./calendar_notes")
        self.date_format = config.get("date_format", "%Y-%m-%d")
        self.use_frontmatter = config.get("frontmatter", True)
        self.organize_by = config.get("organize_by", "date")  # date, category, flat

    @property
    def name(self) -> str:
        return "Markdown 文件"

    def validate_config(self) -> list[str]:
        return []

    def write(self, event: CalendarEvent, classification: Classification) -> str:
        output = Path(self.output_dir)

        # 组织目录结构
        if self.organize_by == "date":
            date_str = event.start_time.strftime("%Y/%m") if event.start_time else "unknown"
            target_dir = output / date_str
        elif self.organize_by == "category":
            target_dir = output / classification.category
        else:
            target_dir = output

        target_dir.mkdir(parents=True, exist_ok=True)

        # 文件名
        date_prefix = event.start_time.strftime(self.date_format) if event.start_time else datetime.now().strftime(self.date_format)
        safe_title = self._safe_filename(event.summary)
        filepath = target_dir / f"{date_prefix} {safe_title}.md"

        # 构建内容
        parts = []
        if self.use_frontmatter:
            fm_lines = [
                "---",
                f"title: \"{event.summary}\"",
                f"date: {event.start_time.isoformat() if event.start_time else ''}",
                f"category: \"{classification.category}\"",
                f"event_type: \"{classification.event_type}\"",
                f"tags: [{', '.join(classification.tags)}]",
                f"source: \"{event.source}\"",
                "---",
            ]
            parts.append("\n".join(fm_lines))
            parts.append("")

        parts.append(f"# {event.summary}")
        parts.append("")

        template_content = build_template(event, classification.event_type, event.source or "日历")
        parts.append(template_content)

        content = "\n".join(parts)
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    @staticmethod
    def _safe_filename(name: str) -> str:
        invalid = '<>:"/\\|?*'
        for c in invalid:
            name = name.replace(c, "")
        return name.strip()[:100]


PluginRegistry.register_writer("markdown", MarkdownWriter)
