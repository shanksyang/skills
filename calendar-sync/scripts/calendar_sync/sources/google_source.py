"""
Google Calendar 日历源插件
"""

from datetime import datetime

from ..base import CalendarSource, CalendarEvent
from ..registry import PluginRegistry


class GoogleCalendarSource(CalendarSource):
    """Google Calendar API 日历源"""

    def __init__(self, config: dict):
        self.config = config
        self.credentials_file = config.get("credentials_file", "credentials.json")
        self.token_file = config.get("token_file", "token.json")
        self.scopes = config.get("scopes", ["https://www.googleapis.com/auth/calendar.readonly"])
        self._service = None

    @property
    def name(self) -> str:
        return "Google Calendar"

    def validate_config(self) -> list[str]:
        import os
        missing = []
        if not os.path.exists(self.credentials_file):
            missing.append(f"source.credentials_file ({self.credentials_file} 不存在)")
        return missing

    def connect(self):
        """使用 OAuth2 连接 Google Calendar API"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "请安装 Google Calendar 依赖: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        import os
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        print("✓ Google Calendar 连接成功")

    def list_calendars(self) -> list[dict]:
        if not self._service:
            raise RuntimeError("请先调用 connect()")

        result = self._service.calendarList().list().execute()
        calendars = result.get("items", [])
        return [
            {"id": cal["id"], "name": cal.get("summary", cal["id"])}
            for cal in calendars
        ]

    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        if not self._service:
            raise RuntimeError("请先调用 connect()")

        print(f"  正在获取 {start.date()} ~ {end.date()} 的日程...")
        events_result = self._service.events().list(
            calendarId=calendar_id,
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        raw_events = events_result.get("items", [])
        events = []
        for raw in raw_events:
            event = self._parse_google_event(raw)
            if event:
                events.append(event)

        print(f"  ✓ 获取到 {len(events)} 个日程事件")
        return events

    def _parse_google_event(self, raw: dict) -> CalendarEvent | None:
        start_str = raw.get("start", {}).get("dateTime") or raw.get("start", {}).get("date", "")
        end_str = raw.get("end", {}).get("dateTime") or raw.get("end", {}).get("date", "")

        start_dt = None
        end_dt = None
        try:
            if "T" in start_str:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            elif start_str:
                start_dt = datetime.fromisoformat(start_str)
        except (ValueError, TypeError):
            pass

        try:
            if "T" in end_str:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            elif end_str:
                end_dt = datetime.fromisoformat(end_str)
        except (ValueError, TypeError):
            pass

        attendees = []
        for att in raw.get("attendees", []):
            attendees.append(att.get("displayName") or att.get("email", ""))

        organizer = raw.get("organizer", {})
        organizer_name = organizer.get("displayName") or organizer.get("email", "")

        return CalendarEvent(
            uid=raw.get("id", ""),
            summary=raw.get("summary", "无标题"),
            description=raw.get("description", ""),
            location=raw.get("location", ""),
            start_time=start_dt,
            end_time=end_dt,
            attendees=attendees,
            organizer=organizer_name,
            source="google",
            raw_data=raw,
        )


PluginRegistry.register_source("google", GoogleCalendarSource)
