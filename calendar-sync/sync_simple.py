#!/usr/bin/env python3
"""企微日历同步到Notion"""
import os
import json
from dotenv import load_dotenv
load_dotenv('/Users/huiyang/Documents/2026/005agents/skills/.env')

import caldav
from icalendar import Calendar
from datetime import datetime, timedelta, timezone
from notion_client import Client

BJ = timezone(timedelta(hours=8))

STATE_FILE = '/Users/huiyang/Documents/2026/005agents/skills/calendar-sync/sync_state.json'

def load_synced_uids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f).get('synced_uids', []))
    return set()

def save_synced_uids(uids):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'synced_uids': sorted(uids), 'last_sync': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

def classify(title):
    t = title.lower()
    if any(k in t for k in ['拜访', '客户', '对接']): return '客户拜访'
    if any(k in t for k in ['会议', '周会', '例会', '培训', '对齐', '分享', '面试']): return '内部会议'
    return '其他事项'

print('连接企微...')
c = caldav.DAVClient(url=os.getenv('WECOM_CALDAV_URL'), username=os.getenv('WECOM_CALDAV_USERNAME'), password=os.getenv('WECOM_CALDAV_PASSWORD'))
cal = c.principal().calendars()[0]

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
start = today
end = today + timedelta(days=3)

print(f'范围: {start.date()} ~ {end.date()}')

synced = load_synced_uids()
print(f'已同步: {len(synced)}')

print('搜索...')
events = cal.search(start=start, end=end, event=True)
print(f'原始: {len(events)}')

evts = []
for e in events:
    if not e.data: continue
    try:
        ical = Calendar.from_ical(e.data)
        for comp in ical.walk():
            if comp.name != 'VEVENT': continue
            uid = str(comp.get('UID', ''))
            summary = str(comp.get('SUMMARY', '无标题'))
            
            dtstart = getattr(comp.get('DTSTART'), 'dt', None)
            dtend = getattr(comp.get('DTEND'), 'dt', None)
            
            start_str = dtstart.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M') if dtstart else ''
            end_str = dtend.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M') if dtend else ''
            
            location = str(comp.get('LOCATION', ''))
            evts.append({'uid': uid, 'summary': summary, 'start': start_str, 'end': end_str, 'location': location})
    except: pass

print(f'有效: {len(evts)}')

print('同步...')
notion = Client(auth=os.getenv('NOTION_TOKEN'))
db_id = os.getenv('NOTION_DATABASE_ID')

new = 0
skip = 0

for ev in evts:
    if ev['uid'] in synced:
        skip += 1
        continue
    
    cat = classify(ev['summary'])
    location = ev['location']
    
    now_iso = datetime.now(tz=BJ).isoformat()
    props = {
        'title': [{'text': {'content': ev['summary']}}],
        '领域': {'select': {'name': '🏢工作'}},
        '分类': {'multi_select': [{'name': cat}]},
        '标签': {'multi_select': [{'name': '周报'}]},
        'Date': {'date': {'start': ev['start'], 'end': ev['end']}},
        'UID': {'rich_text': [{'text': {'content': ev['uid']}}]},
        '创建时间': {'date': {'start': now_iso}},
        '更新时间': {'date': {'start': now_iso}},
    }
    
    # 地点字段处理：只取前30字符，且不能为空
    if location and location != 'None' and len(location) <= 30:
        props['地点'] = {'select': {'name': location}}
    
    try:
        notion.pages.create(parent={'database_id': db_id}, properties=props)
        synced.add(ev['uid'])
        new += 1
        print(f'  ✓ {ev["start"][:10]} {ev["summary"][:35]} [{cat}]')
    except Exception as ex:
        print(f'  ✗ {ev["summary"][:30]} - {str(ex)[:60]}')

save_synced_uids(synced)
print(f'\n完成! 新增:{new} 跳过:{skip} 累计:{len(synced)}')
