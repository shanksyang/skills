"""
插件基类定义 - 所有插件的抽象接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class CalendarEvent:
    """统一的日历事件数据结构"""
    uid: str
    summary: str
    description: str = ""
    location: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendees: list[str] = field(default_factory=list)
    organizer: str = ""
    source: str = ""  # 来源标识，如 "wecom-caldav", "google", "outlook"
    raw_data: Any = None  # 原始数据，供插件使用


@dataclass
class Classification:
    """AI 分类结果"""
    category: str = "其他"
    tags: list[str] = field(default_factory=lambda: ["工作"])
    event_type: str = "other"  # meeting, visit, review, training, social, report, other
    confidence: float = 0.0


class CalendarSource(ABC):
    """日历源插件基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        ...

    @abstractmethod
    def connect(self) -> None:
        """建立连接"""
        ...

    @abstractmethod
    def list_calendars(self) -> list[dict]:
        """列出可用日历，返回 [{"id": ..., "name": ...}, ...]"""
        ...

    @abstractmethod
    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        """获取指定日历在时间范围内的事件"""
        ...

    def validate_config(self) -> list[str]:
        """验证配置，返回缺失项列表"""
        return []


class AIClassifier(ABC):
    """AI 分类器插件基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def classify(self, event: CalendarEvent) -> Classification:
        """对事件进行分类"""
        ...

    def validate_config(self) -> list[str]:
        return []


class NoteWriter(ABC):
    """笔记输出插件基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def write(self, event: CalendarEvent, classification: Classification) -> str:
        """写入笔记，返回笔记的 URL 或路径"""
        ...

    def validate_config(self) -> list[str]:
        return []
