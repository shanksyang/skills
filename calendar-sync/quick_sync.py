#!/usr/bin/env python3
"""极简同步 - 不调用AI"""
import os
import sys
from dotenv import load_dotenv
load_dotenv('/Users/huiyang/Documents/2026/005agents/skills/.env')

sys.stdout.reconfigure(line_buffering=True)

import caldav
from datetime import datetime, timedelta, timezone
from notion_client import Client

BJ = timezone(timedelta(hours=8))

print("连接企微日历...", flush=True)

client = caldav.DAVClient(
    url=os.getenv('WECOM_CALDAV_URL'),
    username=os.getenv('WECOM_CALDAV_USERNAME'),
    password=os.getenv('WECOM_CALDAV_PASSWORD')
)
principal = client.principal()
calendars = principal.calendars()
main_cal = calendars[0]

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
start = today - timedelta(days=2)
end = today + timedelta(days=3)

print(f"范围: {start.date()} ~ {end.date()}", flush=True)

events = main_cal.search(start=start, end=end, event=True, expand=True)
print(f"获取 {len(events)} 个事件", flush=True)

print("连接Notion...", flush=True)
notion = Client(auth=os.getenv('NOTION_TOKEN'))
db_id = os.getenv('NOTION_DATABASE_ID')

created = 0
for e in events:
    ical_inst = e._icalendar_instance
    if not ical_inst:
        continue
    for comp in ical_inst.walk():
        if comp.name != 'VEVENT':
            continue
        summary = str(comp.get('SUMMARY', '无标题'))
        dtstart = comp.get('DTSTART')
        dtend = comp.get('DTEND')
        location = str(comp.get('LOCATION', ''))
        
        # 时间处理
        start_dt = getattr(dtstart, 'dt', None)
        end_dt = getattr(dtend, 'dt', None)
        if start_dt and hasattr(start_dt, 'replace'):
            start_dt = start_dt.replace(tzinfo=None)
            start_str = start_dt.strftime('%Y-%m-%d %H:%M')
        else:
            start_str = str(start_dt) if start_dt else ''
        if end_dt and hasattr(end_dt, 'replace'):
            end_dt = end_dt.replace(tzinfo=None)
            end_str = end_dt.strftime('%Y-%m-%d %H:%M')
        else:
            end_str = str(end_dt) if end_dt else ''
        
        # 简单分类
        cat = "其他事项"
        if any(x in summary for x in ['拜访', '客户']):
            cat = "客户拜访"
        elif any(x in summary for x in ['会议', '周会', '例会', '培训', 'Forecast', '对齐', '分享']):
            cat = "内部会议"
        
        now_iso = datetime.now(tz=BJ).isoformat()
        props = {
            "title": [{"text": {"content": summary}}],
            "领域": {"select": {"name": "🏢工作"}},
            "分类": {"multi_select": [{"name": cat}]},
            "标签": {"multi_select": [{"name": "周报"}]},
            "Date": {"date": {"start": start_str, "end": end_str}},
            "创建时间": {"date": {"start": now_iso}},
            "更新时间": {"date": {"start": now_iso}},
        }
        if location and location != 'None':
            props["地点"] = {"rich_text": [{"text": {"content": location}}]}
        
        try:
            notion.pages.create(parent={"database_id": db_id}, properties=props)
            print(f"✓ {start_str[:10]} {summary[:30]}", flush=True)
            created += 1
        except Exception as ex:
            print(f"✗ {summary[:20]} - {str(ex)[:50]}", flush=True)

print(f"\n完成: {created} 条", flush=True)
