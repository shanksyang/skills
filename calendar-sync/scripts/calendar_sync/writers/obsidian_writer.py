"""
Obsidian 笔记输出插件 - 生成 Markdown 文件到 Obsidian Vault
"""

from datetime import datetime
from pathlib import Path

from ..base import NoteWriter, CalendarEvent, Classification
from ..registry import PluginRegistry
from .templates import build_template


class ObsidianWriter(NoteWriter):
    """Obsidian Vault 笔记输出"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.vault_path = config.get("vault_path", "")
        self.folder = config.get("folder", "Calendar")  # Vault 内的子目录
        self.template_type = config.get("template", "default")  # default, daily-note
        self.use_frontmatter = config.get("frontmatter", True)
        self.date_format = config.get("date_format", "%Y-%m-%d")
        self.tags_prefix = config.get("tags_prefix", "#")

    @property
    def name(self) -> str:
        return "Obsidian"

    def validate_config(self) -> list[str]:
        missing = []
        if not self.vault_path:
            missing.append("output.vault_path")
        elif not Path(self.vault_path).exists():
            missing.append(f"output.vault_path ({self.vault_path} 路径不存在)")
        return missing

    def write(self, event: CalendarEvent, classification: Classification) -> str:
        vault = Path(self.vault_path)
        target_dir = vault / self.folder
        target_dir.mkdir(parents=True, exist_ok=True)

        # 文件名：日期 + 标题
        date_str = event.start_time.strftime(self.date_format) if event.start_time else datetime.now().strftime(self.date_format)
        safe_title = self._safe_filename(event.summary)
        filename = f"{date_str} {safe_title}.md"
        filepath = target_dir / filename

        # 构建内容
        content = self._build_content(event, classification)
        filepath.write_text(content, encoding="utf-8")

        return str(filepath)

    def _build_content(self, event: CalendarEvent, classification: Classification) -> str:
        parts = []

        # YAML frontmatter
        if self.use_frontmatter:
            tags = [t.replace(" ", "-") for t in classification.tags]
            fm_lines = [
                "---",
                f"title: \"{event.summary}\"",
                f"date: {event.start_time.strftime('%Y-%m-%dT%H:%M') if event.start_time else ''}",
                f"category: \"{classification.category}\"",
                f"event_type: \"{classification.event_type}\"",
                f"tags: [{', '.join(tags)}]",
            ]
            if event.location:
                fm_lines.append(f"location: \"{event.location}\"")
            if event.organizer:
                fm_lines.append(f"organizer: \"{event.organizer}\"")
            fm_lines.append(f"source: \"{event.source}\"")
            fm_lines.append("---")
            parts.append("\n".join(fm_lines))
            parts.append("")

        # 标题
        parts.append(f"# {event.summary}")
        parts.append("")

        # 标签行
        tag_line = " ".join(f"{self.tags_prefix}{t}" for t in classification.tags)
        parts.append(tag_line)
        parts.append("")

        # 模板内容
        template_content = build_template(event, classification.event_type, event.source or "日历")
        parts.append(template_content)

        return "\n".join(parts)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """移除文件名中的非法字符"""
        invalid = '<>:"/\\|?*'
        for c in invalid:
            name = name.replace(c, "")
        return name.strip()[:100]


PluginRegistry.register_writer("obsidian", ObsidianWriter)
