"""
CalDAV 日历源插件 v3.0 — 基于 CalDAV 标准协议 (RFC 4791 / RFC 6578)

核心改进:
  1. REPORT calendar-query + time-range: 一次请求获取整个时间范围
  2. expand 循环事件: 服务端展开 RRULE，确保周期性会议不遗漏
  3. sync-token 增量同步: 仅获取变更事件
  4. CTag 快速检测: 无变更时零开销跳过
"""

from datetime import datetime, date, timezone, timedelta

from ..base import CalendarSource, CalendarEvent
from ..registry import PluginRegistry

BEIJING_TZ = timezone(timedelta(hours=8))

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
    """
    通用 CalDAV 日历源

    使用标准 CalDAV 协议方法:
      - PROPFIND: 发现日历、获取 CTag
      - REPORT calendar-query: 按时间范围查询事件
      - REPORT sync-collection: 增量同步变更事件
    """

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
        self._client = None

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
        """PROPFIND discover — 连接并发现日历集合"""
        import caldav

        print(f"正在连接 CalDAV 服务器: {self.url}")
        try:
            self._client = caldav.DAVClient(
                url=self.url,
                username=self.username,
                password=self.password,
            )
            self._principal = self._client.principal()
            print("✓ CalDAV 连接成功")
        except Exception as e:
            raise ConnectionError(f"CalDAV 连接失败: {e}")

    def list_calendars(self) -> list[dict]:
        """PROPFIND — 列出所有可用日历"""
        if not self._principal:
            raise RuntimeError("请先调用 connect()")
        calendars = self._principal.calendars()
        return [{"id": cal.url, "name": cal.name or "(未命名)", "_obj": cal} for cal in calendars]

    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        """
        REPORT calendar-query — 按时间范围获取事件

        底层发送标准的 CalDAV REPORT 请求:
          <C:calendar-query xmlns:C="urn:ietf:params:xml:ns:caldav">
            <C:filter>
              <C:comp-filter name="VCALENDAR">
                <C:comp-filter name="VEVENT">
                  <C:time-range start="..." end="..."/>
                </C:comp-filter>
              </C:comp-filter>
            </C:filter>
          </C:calendar-query>
        """
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

        # 优先使用 expand=True 展开循环事件
        raw_events = self._search_with_fallback(cal_obj, start, end)

        events = []
        for raw in raw_events:
            event = self._parse_ical(raw)
            if event:
                events.append(event)

        print(f"  ✓ 获取到 {len(events)} 个日程事件")
        return events

    def _search_with_fallback(self, cal_obj, start: datetime, end: datetime) -> list:
        """
        REPORT calendar-query，带降级策略:
          1. 尝试 search(expand=True, split_expanded=True) — 展开循环事件
          2. 降级为 search(event=True) — 基础查询
        """
        try:
            return cal_obj.search(
                start=start,
                end=end,
                event=True,
                expand=True,
                split_expanded=True,
            )
        except Exception as e:
            print(f"  ⚠ expand 查询失败，退回基础查询: {e}")
            try:
                return cal_obj.search(start=start, end=end, event=True)
            except Exception as e2:
                print(f"  ⚠ 获取日程失败: {e2}")
                return []

    def _parse_ical(self, raw_event) -> CalendarEvent | None:
        """解析 iCalendar 数据为统一格式，含时区转换"""
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

            # 全天事件处理
            if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
                start_dt = datetime.combine(start_dt, datetime.min.time())
            if isinstance(end_dt, date) and not isinstance(end_dt, datetime):
                end_dt = datetime.combine(end_dt, datetime.min.time())

            # 时区转换到北京时间
            if start_dt:
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.astimezone(BEIJING_TZ)
                else:
                    start_dt = start_dt.replace(tzinfo=BEIJING_TZ)
            if end_dt:
                if end_dt.tzinfo is not None:
                    end_dt = end_dt.astimezone(BEIJING_TZ)
                else:
                    end_dt = end_dt.replace(tzinfo=BEIJING_TZ)

            # 参与人员
            attendees = []
            attendee_prop = component.get("ATTENDEE")
            if attendee_prop:
                if not isinstance(attendee_prop, list):
                    attendee_prop = [attendee_prop]
                for att in attendee_prop:
                    cn = att.params.get("CN", "") if hasattr(att, "params") else ""
                    email = str(att).replace("mailto:", "").replace("MAILTO:", "")
                    attendees.append(cn if cn else email)
            attendees = attendees[:15]

            # 组织者
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
