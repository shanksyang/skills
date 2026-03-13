#!/usr/bin/env python3
"""企微日历同步 - 分批按天查询优化版"""
import os
import json
import time
from dotenv import load_dotenv

# 动态获取项目根目录
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
load_dotenv(os.path.join(_PROJECT_ROOT, '.env'))

import caldav
from icalendar import Calendar
from datetime import datetime, timedelta, timezone
import httpx
import sys

# 添加超时和缓冲
import socket
socket.setdefaulttimeout(30)

BEIJING_TZ = timezone(timedelta(hours=8))

STATE_FILE = os.path.join(_SCRIPT_DIR, 'sync_state.json')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DB_ID = os.getenv('NOTION_DATABASE_ID')

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

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

def query_day(cal, date):
    """按天查询事件，带超时保护
    
    注意: 企微 CalDAV search 有时会返回不在日期范围内的事件，
    需要在解析时过滤
    """
    try:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        # 使用 search (比 date_search 更可靠)
        events = cal.search(start=start, end=end, event=True)
        return events
    except Exception as e:
        print(f"    ⚠ {date}: {str(e)[:30]}", flush=True)
        return []

def filter_events_by_date(events, target_date):
    """过滤事件，只保留目标日期的事件"""
    filtered = []
    target_str = target_date.strftime('%Y-%m-%d')
    
    for e in events:
        if not e.data:
            continue
        try:
            ical = Calendar.from_ical(e.data)
            for comp in ical.walk():
                if comp.name != 'VEVENT':
                    continue
                dtstart = comp.get('DTSTART')
                if dtstart:
                    dt = dtstart.dt
                    # 处理不同类型
                    if hasattr(dt, 'date'):
                        date_str = dt.date().strftime('%Y-%m-%d')
                    else:
                        date_str = str(dt)[:10]
                    
                    # 只保留目标日期的事件
                    if date_str == target_str:
                        filtered.append(e)
                        break
        except:
            pass
    
    return filtered

def sync_events_to_notion(evts, synced):
    """同步事件到Notion"""
    new = 0
    skip = 0
    
    for ev in evts:
        if ev['uid'] in synced:
            skip += 1
            continue
        
        cat = classify(ev['summary'])
        location = ev['location']
        
        now_iso = datetime.now(tz=BEIJING_TZ).isoformat()
        properties = {
            'title': {'title': [{'text': {'content': ev['summary']}}]},
            '领域': {'select': {'name': '🏢工作'}},
            '分类': {'multi_select': [{'name': cat}]},
            '标签': {'multi_select': [{'name': '周报'}]},
            'Date': {'date': {'start': ev['start'], 'end': ev['end']}},
            'UID': {'rich_text': [{'text': {'content': ev['uid']}}]},
            '创建时间': {'date': {'start': now_iso}},
            '更新时间': {'date': {'start': now_iso}},
        }
        
        if location and location != 'None' and len(location) <= 30:
            properties['地点'] = {'select': {'name': location}}
        
        if ev['attendees']:
            att_str = ', '.join(ev['attendees'])
            properties['人员'] = {'rich_text': [{'text': {'content': att_str}}]}
        
        try:
            resp = httpx.post('https://api.notion.com/v1/pages', headers=HEADERS, json={'parent': {'database_id': DB_ID}, 'properties': properties}, timeout=10)
            if resp.status_code == 200:
                synced.add(ev['uid'])
                new += 1
                print(f"    ✓ {ev['start']} {ev['summary'][:30]}", flush=True)
            else:
                err = resp.text[:80]
                if 'already exists' in err or '409' in err:
                    synced.add(ev['uid'])
                    print(f"    ⊘ 已存在: {ev['summary'][:30]}", flush=True)
                else:
                    print(f"    ✗ {ev['summary'][:20]} - {err}", flush=True)
        except Exception as ex:
            print(f"    ✗ 异常: {str(ex)[:50]}", flush=True)
    
    return new, skip

def main():
    print('=' * 50)
    print('企微日历同步 - 分批按天查询优化版')
    print('=' * 50)
    
    # 连接企微
    print('\n[1/4] 连接企微...', flush=True)
    try:
        c = caldav.DAVClient(url=os.getenv('WECOM_CALDAV_URL'), username=os.getenv('WECOM_CALDAV_USERNAME'), password=os.getenv('WECOM_CALDAV_PASSWORD'))
        cal = c.principal().calendars()[0]
        print(f"    ✓ 日历: {cal.name}", flush=True)
    except Exception as e:
        print(f"    ✗ 连接失败: {e}", flush=True)
        return
    
    # 加载已同步
    synced = load_synced_uids()
    print(f"    ✓ 已同步: {len(synced)} 条", flush=True)
    
    # 设置查询范围 (今天+未来14天)
    today = datetime.now().date()
    days = [(today + timedelta(days=i)) for i in range(15)]
    
    print(f'\n[2/4] 分批查询 {len(days)} 天...', flush=True)
    print(f'    范围: {days[0]} ~ {days[-1]}', flush=True)
    
    # 按天查询
    all_events = []
    success_days = 0
    fail_days = 0
    
    for i, day in enumerate(days):
        print(f"    [{i+1}/{len(days)}] {day}...", end=" ", flush=True)
        sys.stdout.flush()
        
        try:
            events = query_day(cal, day)
            # 企微 CalDAV 有时会返回不在查询范围内的事件，需要过滤
            events = filter_events_by_date(events, day)
            print(f"{len(events)}个", flush=True)
            
            # 解析事件
            for e in events:
                if not e.data:
                    continue
                try:
                    ical = Calendar.from_ical(e.data)
                    for comp in ical.walk():
                        if comp.name != 'VEVENT':
                            continue
                        
                        uid = str(comp.get('UID', ''))
                        summary = str(comp.get('SUMMARY', '无标题'))
                        
                        dtstart = getattr(comp.get('DTSTART'), 'dt', None)
                        dtend = getattr(comp.get('DTEND'), 'dt', None)
                        
                        # 时区转换
                        if dtstart:
                            if dtstart.tzinfo is not None:
                                dtstart = dtstart.astimezone(BEIJING_TZ)
                            else:
                                dtstart = dtstart.replace(tzinfo=BEIJING_TZ)
                        if dtend:
                            if dtend.tzinfo is not None:
                                dtend = dtend.astimezone(BEIJING_TZ)
                            else:
                                dtend = dtend.replace(tzinfo=BEIJING_TZ)
                        
                        start_str = dtstart.strftime('%Y-%m-%d') if dtstart else ''
                        end_str = dtend.strftime('%Y-%m-%d') if dtend else ''
                        
                        location = str(comp.get('LOCATION', ''))
                        
                        # 提取参与人员
                        attendees = []
                        attendee_prop = comp.get("ATTENDEE")
                        if attendee_prop:
                            if not isinstance(attendee_prop, list):
                                attendee_prop = [attendee_prop]
                            for att in attendee_prop:
                                cn = str(att.params.get('CN', '')) if hasattr(att, 'params') else ''
                                email = str(att).replace('mailto:', '')
                                name = cn if cn else email.split('@')[0] if '@' in email else email
                                if name:
                                    attendees.append(name)
                        attendees = attendees[:10]
                        
                        all_events.append({
                            'uid': uid, 'summary': summary,
                            'start': start_str, 'end': end_str,
                            'location': location, 'attendees': attendees
                        })
                except Exception as parse_err:
                    print(f"      ⚠ 解析错误: {parse_err}", flush=True)
            
            success_days += 1
        except Exception as e:
            print(f"失败", flush=True)
            fail_days += 1
        
        # 每次查询后短暂休息，避免请求过快
        time.sleep(0.5)
    
    print(f'\n    查询完成: {success_days} 天成功, {fail_days} 天失败', flush=True)
    print(f'    共获取 {len(all_events)} 个事件', flush=True)
    
    # 同步到Notion
    print(f'\n[3/4] 同步到 Notion...', flush=True)
    new_count, skip_count = sync_events_to_notion(all_events, synced)
    
    # 保存状态
    save_synced_uids(synced)
    
    print(f'\n[4/4] 完成!', flush=True)
    print(f'    新增: {new_count}', flush=True)
    print(f'    跳过: {skip_count}', flush=True)
    print(f'    累计: {len(synced)}', flush=True)

if __name__ == '__main__':
    main()
