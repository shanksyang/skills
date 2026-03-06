"""
iCal 文件/URL 日历源插件 - 支持 .ics 文件和订阅 URL
"""

from datetime import datetime, date
from pathlib import Path

from ..base import CalendarSource, CalendarEvent
from ..registry import PluginRegistry


class ICalFileSource(CalendarSource):
    """iCalendar 文件/URL 日历源（支持 .ics 文件和订阅链接）"""

    def __init__(self, config: dict):
        self.config = config
        self.paths = config.get("paths", [])  # .ics 文件路径列表
        self.urls = config.get("urls", [])  # 订阅 URL 列表
        self._calendars_data = {}  # name -> ical_text

    @property
    def name(self) -> str:
        return "iCal 文件/URL"

    def validate_config(self) -> list[str]:
        if not self.paths and not self.urls:
            return ["source.paths 或 source.urls (至少需要一个)"]
        return []

    def connect(self):
        """加载所有 iCal 数据"""
        for path_str in self.paths:
            path = Path(path_str)
            if path.exists():
                self._calendars_data[path.stem] = path.read_text(encoding="utf-8")
                print(f"✓ 已加载文件: {path}")
            else:
                print(f"⚠ 文件不存在: {path}")

        for url in self.urls:
            try:
                import requests
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                cal_name = url.split("/")[-1].replace(".ics", "") or "subscription"
                self._calendars_data[cal_name] = resp.text
                print(f"✓ 已加载 URL: {url}")
            except Exception as e:
                print(f"⚠ 加载 URL 失败 ({url}): {e}")

        if not self._calendars_data:
            raise ConnectionError("没有成功加载任何日历数据")

    def list_calendars(self) -> list[dict]:
        return [
            {"id": name, "name": name}
            for name in self._calendars_data
        ]

    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        from icalendar import Calendar as iCalendar

        ical_text = self._calendars_data.get(calendar_id, "")
        if not ical_text:
            return []

        print(f"  正在解析 {start.date()} ~ {end.date()} 的日程...")
        try:
            cal = iCalendar.from_ical(ical_text)
        except Exception as e:
            print(f"  ⚠ 解析失败: {e}")
            return []

        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            dtstart = component.get("DTSTART")
            start_dt = dtstart.dt if dtstart else None
            if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
                start_dt = datetime.combine(start_dt, datetime.min.time())

            # 过滤时间范围
            if start_dt:
                if start_dt < start or start_dt > end:
                    continue

            dtend = component.get("DTEND")
            end_dt = dtend.dt if dtend else None
            if isinstance(end_dt, date) and not isinstance(end_dt, datetime):
                end_dt = datetime.combine(end_dt, datetime.min.time())

            attendees = []
            attendee_prop = component.get("ATTENDEE")
            if attendee_prop:
                if not isinstance(attendee_prop, list):
                    attendee_prop = [attendee_prop]
                for att in attendee_prop:
                    cn = att.params.get("CN", "") if hasattr(att, "params") else ""
                    email = str(att).replace("mailto:", "").replace("MAILTO:", "")
                    attendees.append(cn if cn else email)

            organizer = component.get("ORGANIZER")
            organizer_name = ""
            if organizer:
                cn = organizer.params.get("CN", "") if hasattr(organizer, "params") else ""
                organizer_name = cn if cn else str(organizer).replace("mailto:", "")

            events.append(CalendarEvent(
                uid=str(component.get("UID", "")),
                summary=str(component.get("SUMMARY", "无标题")),
                description=str(component.get("DESCRIPTION", "")),
                location=str(component.get("LOCATION", "")),
                start_time=start_dt,
                end_time=end_dt,
                attendees=attendees,
                organizer=organizer_name,
                source="ical-file",
            ))

        print(f"  ✓ 获取到 {len(events)} 个日程事件")
        return events


PluginRegistry.register_source("ical", ICalFileSource)
