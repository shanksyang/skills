"""
Logseq 笔记输出插件 - 生成大纲格式的 Markdown 文件到 Logseq 图谱
"""

from datetime import datetime
from pathlib import Path

from ..base import NoteWriter, CalendarEvent, Classification
from ..registry import PluginRegistry


class LogseqWriter(NoteWriter):
    """Logseq 图谱笔记输出（大纲格式）"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.graph_path = config.get("graph_path", "")
        self.folder = config.get("folder", "pages")
        self.use_journal = config.get("journal", False)  # 是否写入日记页
        self.journal_folder = config.get("journal_folder", "journals")
        self.date_format = config.get("date_format", "%Y_%m_%d")

    @property
    def name(self) -> str:
        return "Logseq"

    def validate_config(self) -> list[str]:
        missing = []
        if not self.graph_path:
            missing.append("output.graph_path")
        elif not Path(self.graph_path).exists():
            missing.append(f"output.graph_path ({self.graph_path} 路径不存在)")
        return missing

    def write(self, event: CalendarEvent, classification: Classification) -> str:
        graph = Path(self.graph_path)

        if self.use_journal:
            return self._write_to_journal(graph, event, classification)
        else:
            return self._write_to_page(graph, event, classification)

    def _write_to_page(self, graph: Path, event: CalendarEvent, classification: Classification) -> str:
        """写入独立页面"""
        target_dir = graph / self.folder
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_title = self._safe_filename(event.summary)
        filepath = target_dir / f"{safe_title}.md"

        content = self._build_page_content(event, classification)
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def _write_to_journal(self, graph: Path, event: CalendarEvent, classification: Classification) -> str:
        """追加到日记页"""
        journal_dir = graph / self.journal_folder
        journal_dir.mkdir(parents=True, exist_ok=True)

        date_str = event.start_time.strftime(self.date_format) if event.start_time else datetime.now().strftime(self.date_format)
        filepath = journal_dir / f"{date_str}.md"

        block = self._build_journal_block(event, classification)

        # 追加到已有日记
        existing = filepath.read_text(encoding="utf-8") if filepath.exists() else ""
        with open(filepath, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(block)

        return str(filepath)

    def _build_page_content(self, event: CalendarEvent, classification: Classification) -> str:
        """构建 Logseq 页面内容（大纲格式）"""
        lines = []

        # 属性
        tags = " ".join(f"[[{t}]]" for t in classification.tags)
        lines.append(f"category:: {classification.category}")
        lines.append(f"event-type:: {classification.event_type}")
        lines.append(f"tags:: {tags}")
        if event.start_time:
            lines.append(f"date:: [[{event.start_time.strftime('%Y-%m-%d')}]]")
        if event.location:
            lines.append(f"location:: {event.location}")
        if event.source:
            lines.append(f"source:: {event.source}")
        lines.append("")

        # 事件信息
        lines.append(f"- 📅 **{event.summary}**")
        if event.start_time:
            time_str = event.start_time.strftime("%Y-%m-%d %H:%M")
            if event.end_time:
                time_str += f" ~ {event.end_time.strftime('%H:%M')}"
            lines.append(f"  - 🕐 {time_str}")
        if event.location:
            lines.append(f"  - 📍 {event.location}")
        if event.organizer:
            lines.append(f"  - 👤 {event.organizer}")

        # 模板
        template = self._get_template(classification.event_type)
        for item in template:
            lines.append(f"- {item}")

        if event.description:
            lines.append("- **原始描述**")
            for line in event.description.split("\n")[:20]:
                lines.append(f"  - {line}")

        lines.append(f"- *自动同步自{event.source or '日历'}*")
        return "\n".join(lines)

    def _build_journal_block(self, event: CalendarEvent, classification: Classification) -> str:
        """构建追加到日记的大纲块"""
        lines = []
        tag_str = " ".join(f"#{t}" for t in classification.tags)
        time_str = event.start_time.strftime("%H:%M") if event.start_time else ""

        lines.append(f"- {time_str} 📅 **{event.summary}** {tag_str}")
        lines.append(f"  - 分类: {classification.category}")
        if event.location:
            lines.append(f"  - 地点: {event.location}")

        template = self._get_template(classification.event_type)
        for item in template:
            lines.append(f"  - {item}")

        lines.append("")
        return "\n".join(lines)

    def _get_template(self, event_type: str) -> list[str]:
        templates = {
            "meeting": ["**会议议题**", "  - TODO 议题1", "**会议纪要**", "  - ", "**待办事项**", "  - TODO "],
            "visit": ["**拜访目的**", "  - ", "**沟通要点**", "  - TODO 要点1", "**后续跟进**", "  - TODO "],
            "review": ["**评审内容**", "  - ", "**关键结论**", "  - ", "**后续行动**", "  - TODO "],
            "training": ["**学习主题**", "  - ", "**核心收获**", "  - ", "**实践计划**", "  - TODO "],
            "social": ["**活动记录**", "  - "],
            "report": ["**汇报主题**", "  - ", "**核心内容**", "  - ", "**后续跟进**", "  - TODO "],
            "other": ["**笔记**", "  - "],
        }
        return templates.get(event_type, templates["other"])

    @staticmethod
    def _safe_filename(name: str) -> str:
        invalid = '<>:"/\\|?*'
        for c in invalid:
            name = name.replace(c, "")
        return name.strip()[:100]


PluginRegistry.register_writer("logseq", LogseqWriter)
