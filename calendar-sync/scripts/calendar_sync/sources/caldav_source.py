"""
CalDAV 日历源插件 - 支持企业微信、iCloud、Nextcloud 等 CalDAV 兼容服务
"""

from datetime import datetime, date

from ..base import CalendarSource, CalendarEvent
from ..registry import PluginRegistry


# 预设的 CalDAV 服务配置
CALDAV_PRESETS = {
    "wecom": {
        "url": "https://caldav.wecom.work/calendar/",
        "name": "企业微信",
    },
    "icloud": {
        "url": "https://caldav.icloud.com/",
        "name": "iCloud",
    },
    "nextcloud": {
        "url_template": "{server}/remote.php/dav/calendars/{username}/",
        "name": "Nextcloud",
    },
    "synology": {
        "url_template": "{server}/caldav/{username}/",
        "name": "Synology",
    },
}


class CalDAVSource(CalendarSource):
    """通用 CalDAV 日历源"""

    def __init__(self, config: dict):
        self.config = config
        preset = config.get("preset", "")
        self._name = "CalDAV"

        if preset and preset in CALDAV_PRESETS:
            preset_cfg = CALDAV_PRESETS[preset]
            self._name = f"CalDAV ({preset_cfg['name']})"
            if "url" in preset_cfg:
                self.url = config.get("url", preset_cfg["url"])
            elif "url_template" in preset_cfg:
                self.url = preset_cfg["url_template"].format(
                    server=config.get("server", ""),
                    username=config.get("username", ""),
                )
            else:
                self.url = config.get("url", "")
        else:
            self.url = config.get("url", "")

        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self._principal = None

    @property
    def name(self) -> str:
        return self._name

    def validate_config(self) -> list[str]:
        missing = []
        if not self.url:
            missing.append("source.url")
        if not self.username:
            missing.append("source.username")
        if not self.password:
            missing.append("source.password")
        return missing

    def connect(self):
        import caldav

        print(f"正在连接 CalDAV 服务器: {self.url}")
        try:
            client = caldav.DAVClient(
                url=self.url,
                username=self.username,
                password=self.password,
            )
            self._principal = client.principal()
            print("✓ CalDAV 连接成功")
        except Exception as e:
            raise ConnectionError(f"CalDAV 连接失败: {e}")

    def list_calendars(self) -> list[dict]:
        if not self._principal:
            raise RuntimeError("请先调用 connect()")
        calendars = self._principal.calendars()
        return [{"id": cal.url, "name": cal.name or "(未命名)", "_obj": cal} for cal in calendars]

    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        from icalendar import Calendar as iCalendar

        # 查找对应的 calendar 对象
        calendars = self._principal.calendars()
        cal_obj = None
        for cal in calendars:
            if cal.url == calendar_id:
                cal_obj = cal
                break

        if not cal_obj:
            print(f"  ⚠ 未找到日历: {calendar_id}")
            return []

        print(f"  正在获取 {start.date()} ~ {end.date()} 的日程...")
        try:
            raw_events = cal_obj.search(start=start, end=end, event=True, expand=True)
        except Exception as e:
            print(f"  ⚠ 获取日程失败: {e}")
            return []

        events = []
        for raw in raw_events:
            event = self._parse_ical(raw)
            if event:
                events.append(event)

        print(f"  ✓ 获取到 {len(events)} 个日程事件")
        return events

    def _parse_ical(self, raw_event) -> CalendarEvent | None:
        """解析 iCalendar 数据为统一格式"""
        from icalendar import Calendar as iCalendar

        try:
            cal = iCalendar.from_ical(raw_event.data)
        except Exception as e:
            print(f"  ⚠ 解析 iCal 数据失败: {e}")
            return None

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            uid = str(component.get("UID", ""))
            summary = str(component.get("SUMMARY", "无标题"))
            description = str(component.get("DESCRIPTION", ""))
            location = str(component.get("LOCATION", ""))

            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            start_dt = dtstart.dt if dtstart else None
            end_dt = dtend.dt if dtend else None

            if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
                start_dt = datetime.combine(start_dt, datetime.min.time())
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

            return CalendarEvent(
                uid=uid,
                summary=summary,
                description=description,
                location=location,
                start_time=start_dt,
                end_time=end_dt,
                attendees=attendees,
                organizer=organizer_name,
                source=f"caldav:{self.config.get('preset', 'generic')}",
            )
        return None


# 注册插件
PluginRegistry.register_source("caldav", CalDAVSource)
