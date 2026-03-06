"""
Outlook / Microsoft 365 日历源插件 (Microsoft Graph API)
"""

from datetime import datetime

from ..base import CalendarSource, CalendarEvent
from ..registry import PluginRegistry


class OutlookSource(CalendarSource):
    """Microsoft Outlook / Exchange 日历源 (通过 Graph API)"""

    def __init__(self, config: dict):
        self.config = config
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.tenant_id = config.get("tenant_id", "common")
        self.token_file = config.get("token_file", "outlook_token.json")
        self._headers = {}

    @property
    def name(self) -> str:
        return "Outlook / Microsoft 365"

    def validate_config(self) -> list[str]:
        missing = []
        if not self.client_id:
            missing.append("source.client_id")
        return missing

    def connect(self):
        """使用 MSAL 进行 OAuth2 认证"""
        try:
            import msal
        except ImportError:
            raise ImportError("请安装 Microsoft 依赖: pip install msal requests")

        import json
        import os

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        scopes = ["https://graph.microsoft.com/Calendars.Read"]

        app = msal.PublicClientApplication(self.client_id, authority=authority)

        token_data = None
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                token_data = json.load(f)

        result = None
        if token_data:
            accounts = app.get_accounts()
            if accounts:
                result = app.acquire_token_silent(scopes, account=accounts[0])

        if not result:
            flow = app.initiate_device_flow(scopes=scopes)
            print(f"请在浏览器中访问: {flow['verification_uri']}")
            print(f"输入代码: {flow['user_code']}")
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self._headers = {"Authorization": f"Bearer {result['access_token']}"}
            with open(self.token_file, "w") as f:
                json.dump(result, f)
            print("✓ Outlook 连接成功")
        else:
            raise ConnectionError(f"Outlook 认证失败: {result.get('error_description', 'unknown')}")

    def list_calendars(self) -> list[dict]:
        import requests

        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/calendars",
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {"id": cal["id"], "name": cal.get("name", cal["id"])}
            for cal in data.get("value", [])
        ]

    def fetch_events(self, calendar_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        import requests

        print(f"  正在获取 {start.date()} ~ {end.date()} 的日程...")
        params = {
            "startDateTime": start.isoformat() + "Z",
            "endDateTime": end.isoformat() + "Z",
            "$orderby": "start/dateTime",
            "$top": 500,
        }
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/calendarView",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        raw_events = resp.json().get("value", [])

        events = []
        for raw in raw_events:
            event = self._parse_event(raw)
            if event:
                events.append(event)

        print(f"  ✓ 获取到 {len(events)} 个日程事件")
        return events

    def _parse_event(self, raw: dict) -> CalendarEvent | None:
        start_str = raw.get("start", {}).get("dateTime", "")
        end_str = raw.get("end", {}).get("dateTime", "")

        start_dt = None
        end_dt = None
        try:
            start_dt = datetime.fromisoformat(start_str) if start_str else None
        except (ValueError, TypeError):
            pass
        try:
            end_dt = datetime.fromisoformat(end_str) if end_str else None
        except (ValueError, TypeError):
            pass

        attendees = []
        for att in raw.get("attendees", []):
            name = att.get("emailAddress", {}).get("name", "")
            email = att.get("emailAddress", {}).get("address", "")
            attendees.append(name if name else email)

        organizer = raw.get("organizer", {}).get("emailAddress", {})
        organizer_name = organizer.get("name") or organizer.get("address", "")

        return CalendarEvent(
            uid=raw.get("id", ""),
            summary=raw.get("subject", "无标题"),
            description=raw.get("bodyPreview", ""),
            location=raw.get("location", {}).get("displayName", ""),
            start_time=start_dt,
            end_time=end_dt,
            attendees=attendees,
            organizer=organizer_name,
            source="outlook",
            raw_data=raw,
        )


PluginRegistry.register_source("outlook", OutlookSource)
