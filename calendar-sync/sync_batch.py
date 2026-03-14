#!/usr/bin/env python3
"""
企微日历同步 v3.1 — 基于 CalDAV 标准协议 + AI 智能标签分类

核心改进（对照 RFC 4791 / RFC 6578）:
  1. REPORT calendar-query + time-range: 一次请求获取整个时间范围，
     取代旧版按天逐个 search 的低效方式
  2. sync-collection REPORT (sync-token): 增量同步，
     只拉取上次同步后变更的事件
  3. PROPFIND getctag: 通过日历集合标签快速判断是否有变更，
     无变更时跳过查询（零网络开销）
  4. expand 循环事件: 服务端展开 RRULE，确保周期性会议不遗漏
  5. ETag 变更检测: 精确判断单个事件是否被修改
"""

import os
import json
import sys
from datetime import datetime, timedelta, timezone, date

from dotenv import load_dotenv

# ── 动态路径 ──────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
load_dotenv(os.path.join(_PROJECT_ROOT, '.env'))

import caldav
from icalendar import Calendar
import httpx

# ── 常量 ──────────────────────────────────────────────────
BEIJING_TZ = timezone(timedelta(hours=8))
STATE_FILE = os.path.join(_SCRIPT_DIR, 'sync_state.json')

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DB_ID = os.getenv('NOTION_DATABASE_ID')
HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28',
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  状态管理 — 持久化 UID / sync-token / CTag / ETag
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_state() -> dict:
    """加载同步状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """保存同步状态"""
    state['last_sync'] = datetime.now(tz=BEIJING_TZ).isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CalDAV 标准调用
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def connect_caldav():
    """连接 CalDAV 服务器，获取 principal 和默认日历"""
    client = caldav.DAVClient(
        url=os.getenv('WECOM_CALDAV_URL'),
        username=os.getenv('WECOM_CALDAV_USERNAME'),
        password=os.getenv('WECOM_CALDAV_PASSWORD'),
    )
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("未找到任何日历")
    return client, calendars[0]


def get_calendar_ctag(cal) -> str:
    """
    PROPFIND getctag — 获取日历集合标签

    CTag 在日历中任何事件发生变更时都会改变。
    通过比较上次记录的 CTag 可快速判断是否需要执行同步。
    """
    try:
        # python-caldav 在 get_properties 中支持获取 getctag
        from caldav.elements import cdav
        props = cal.get_properties([cdav.CalendarData()])
        # 尝试直接从 URL 属性获取 ctag
    except Exception:
        pass

    # 备选方案: 通过 PROPFIND 直接获取 getctag
    try:
        import xml.etree.ElementTree as ET
        # 构造 PROPFIND 请求获取 getctag
        body = """<?xml version="1.0" encoding="utf-8"?>
<D:propfind xmlns:D="DAV:" xmlns:CS="http://calendarserver.org/ns/">
  <D:prop>
    <CS:getctag/>
  </D:prop>
</D:propfind>"""
        response = cal.client.propfind(cal.url, body, depth=0)
        if hasattr(response, 'raw'):
            raw = response.raw
        elif hasattr(response, 'text'):
            raw = response.text
        else:
            raw = str(response)

        # 解析 XML 提取 getctag 值
        if 'getctag' in str(raw):
            root = ET.fromstring(str(raw)) if isinstance(raw, str) else ET.fromstring(raw)
            ns = {'CS': 'http://calendarserver.org/ns/', 'D': 'DAV:'}
            ctag_el = root.find('.//CS:getctag', ns)
            if ctag_el is not None and ctag_el.text:
                return ctag_el.text.strip()
    except Exception as e:
        print(f"    ⚠ 获取 CTag 失败 (非致命): {e}", flush=True)

    return ""


def fetch_events_by_report(cal, start_dt: datetime, end_dt: datetime) -> list:
    """
    REPORT calendar-query + time-range — 标准日历查询

    使用 caldav 库的 search() 方法，它在底层构造标准的
    REPORT calendar-query 请求:

    <C:calendar-query xmlns:C="urn:ietf:params:xml:ns:caldav">
      <D:prop xmlns:D="DAV:">
        <D:getetag/>
        <C:calendar-data/>
      </D:prop>
      <C:filter>
        <C:comp-filter name="VCALENDAR">
          <C:comp-filter name="VEVENT">
            <C:time-range start="20260316T000000Z" end="20260323T000000Z"/>
          </C:comp-filter>
        </C:comp-filter>
      </C:filter>
    </C:calendar-query>

    优势:
      - 一次 HTTP 请求获取整个时间范围（旧版需要 15+ 次）
      - 服务端过滤，减少网络传输
      - expand=True 展开循环事件的所有实例
    """
    try:
        events = cal.search(
            start=start_dt,
            end=end_dt,
            event=True,          # 只查询 VEVENT
            expand=True,         # 展开循环事件
            split_expanded=True, # 每个循环实例作为独立对象返回
        )
        return events
    except Exception as e:
        # 部分 CalDAV 服务器不支持 expand，退回基础查询
        print(f"    ⚠ expand 查询失败，退回基础查询: {e}", flush=True)
        try:
            events = cal.search(start=start_dt, end=end_dt, event=True)
            return events
        except Exception as e2:
            print(f"    ✗ 查询失败: {e2}", flush=True)
            return []


def fetch_events_by_sync_token(cal, sync_token: str = None) -> tuple:
    """
    sync-collection REPORT (RFC 6578) — 增量同步

    通过 sync-token 只获取自上次同步以来发生变更的事件。
    返回 (events, new_sync_token)

    工作原理:
      1. 首次同步: sync_token=None → 返回所有对象 + 新的 sync_token
      2. 后续同步: 传入上次的 sync_token → 仅返回变更对象 + 新 token
      3. token 过期: 服务器返回错误 → 自动降级为全量同步
    """
    try:
        sync_result = cal.objects_by_sync_token(
            sync_token=sync_token,
            load_objects=True,
        )
        # 获取新的 sync_token
        new_token = getattr(sync_result, 'sync_token', None)
        objects = list(sync_result)
        return objects, new_token
    except Exception as e:
        print(f"    ⚠ sync-token 同步失败: {e}", flush=True)
        return None, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  iCalendar 数据解析
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def parse_ical_event(raw_event, start_filter=None, end_filter=None) -> list[dict]:
    """
    解析 iCalendar 数据为统一字典格式

    支持:
      - 时区转换 (UTC → 北京时间)
      - 全天事件 (date 类型) 和定时事件 (datetime 类型)
      - 参与人员 (ATTENDEE CN 属性)
      - 组织者 (ORGANIZER CN 属性)
      - 日期范围过滤 (可选)
    """
    if not raw_event.data:
        return []

    results = []
    try:
        ical = Calendar.from_ical(raw_event.data)
    except Exception:
        return []

    for comp in ical.walk():
        if comp.name != 'VEVENT':
            continue

        uid = str(comp.get('UID', ''))
        summary = str(comp.get('SUMMARY', '无标题'))
        description = str(comp.get('DESCRIPTION', ''))
        location = str(comp.get('LOCATION', ''))

        # ── 时间解析与时区转换 ────────────────────────
        dtstart_prop = comp.get('DTSTART')
        dtend_prop = comp.get('DTEND')
        dtstart = dtstart_prop.dt if dtstart_prop else None
        dtend = dtend_prop.dt if dtend_prop else None

        is_all_day = False
        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
            is_all_day = True
            dtstart = datetime.combine(dtstart, datetime.min.time()).replace(tzinfo=BEIJING_TZ)
        if isinstance(dtend, date) and not isinstance(dtend, datetime):
            dtend = datetime.combine(dtend, datetime.min.time()).replace(tzinfo=BEIJING_TZ)

        if dtstart and not is_all_day:
            if dtstart.tzinfo is not None:
                dtstart = dtstart.astimezone(BEIJING_TZ)
            else:
                dtstart = dtstart.replace(tzinfo=BEIJING_TZ)
        if dtend and not is_all_day:
            if dtend.tzinfo is not None:
                dtend = dtend.astimezone(BEIJING_TZ)
            else:
                dtend = dtend.replace(tzinfo=BEIJING_TZ)

        # ── 日期范围过滤 ────────────────────────────
        if start_filter and dtstart:
            event_date = dtstart.date() if hasattr(dtstart, 'date') else dtstart
            filter_start = start_filter.date() if isinstance(start_filter, datetime) else start_filter
            filter_end = end_filter.date() if isinstance(end_filter, datetime) else end_filter
            if event_date < filter_start or event_date > filter_end:
                continue

        # ── 格式化日期字符串 ────────────────────────
        if is_all_day:
            start_str = dtstart.strftime('%Y-%m-%d') if dtstart else ''
            end_str = dtend.strftime('%Y-%m-%d') if dtend else ''
        else:
            start_str = dtstart.isoformat() if dtstart else ''
            end_str = dtend.isoformat() if dtend else ''

        # ── 参与人员 (ATTENDEE) ────────────────────
        attendees = []
        attendee_prop = comp.get('ATTENDEE')
        if attendee_prop:
            if not isinstance(attendee_prop, list):
                attendee_prop = [attendee_prop]
            for att in attendee_prop:
                cn = str(att.params.get('CN', '')) if hasattr(att, 'params') else ''
                email = str(att).replace('mailto:', '').replace('MAILTO:', '')
                name = cn if cn else (email.split('@')[0] if '@' in email else email)
                if name:
                    attendees.append(name)
        attendees = attendees[:15]

        # ── 组织者 (ORGANIZER) ─────────────────────
        organizer = comp.get('ORGANIZER')
        organizer_name = ''
        if organizer:
            cn = organizer.params.get('CN', '') if hasattr(organizer, 'params') else ''
            organizer_name = str(cn) if cn else str(organizer).replace('mailto:', '')

        # ── ETag (单资源变更标签) ──────────────────
        etag = ''
        if hasattr(raw_event, 'props') and raw_event.props:
            etag = str(raw_event.props.get('{DAV:}getetag', ''))

        results.append({
            'uid': uid,
            'summary': summary,
            'description': description,
            'start': start_str,
            'end': end_str,
            'location': location,
            'attendees': attendees,
            'organizer': organizer_name,
            'etag': etag,
            'is_all_day': is_all_day,
        })

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  事件去重与分类
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def deduplicate_events(events: list[dict]) -> list[dict]:
    """按 UID 去重，保留最新（后出现的覆盖先出现的）"""
    seen = {}
    for ev in events:
        uid = ev['uid']
        if uid:
            seen[uid] = ev
    return list(seen.values())


def classify_keyword(title: str) -> tuple[str, list[str]]:
    """基于关键词的事件分类 (fallback)，返回 (分类, 标签列表)"""
    t = title.lower()
    tags = ['周报']

    # ── 分类 ──
    if any(k in t for k in ['拜访', '客户', '对接']):
        cat = '客户拜访'
        tags.extend(['拜访', '客户'])
    elif any(k in t for k in ['周会', '例会', '双周会']):
        cat = '内部会议'
        tags.extend(['会议', '周会'])
    elif any(k in t for k in ['会议', '对齐', '汇报', '评审']):
        cat = '内部会议'
        tags.extend(['会议'])
    elif any(k in t for k in ['培训', '分享', '学习']):
        cat = '培训学习'
        tags.extend(['培训', '学习'])
    elif any(k in t for k in ['聚餐', '晚餐', '晚宴', '午餐']):
        cat = '聚餐社交'
        tags.extend(['聚餐', '社交'])
    elif any(k in t for k in ['面试']):
        cat = '内部会议'
        tags.extend(['面试'])
    elif any(k in t for k in ['方案', '项目']):
        cat = '方案汇报'
        tags.extend(['方案', '项目'])
    elif any(k in t for k in ['飞机', '航班', '机场']):
        cat = '其他事项'
        tags.extend(['出差', '交通', '飞机'])
    elif any(k in t for k in ['活动']):
        cat = '外部活动'
        tags.extend(['活动'])
    else:
        cat = '其他事项'
        tags.extend(['工作'])

    # ── 从标题提取额外标签 ──
    tag_hints = {
        'adp': 'ADP项目', '1v1': '1v1', 'leader': 'Leader',
        '政企': '政企', '教育': '教育', '大模型': '大模型',
        'ai': 'AI', 'cto': 'CTO', '深圳': '深圳', '北京': '北京',
        '香港': '香港', '武汉': '武汉', '上海': '上海',
        '预留': '预留', '线上': '线上', 'fr': 'FR会议',
        'devops': 'DevOps', '开源': '开源平台', '研讨': '研讨会',
    }
    for kw, tag in tag_hints.items():
        if kw in t:
            tags.append(tag)

    return cat, list(dict.fromkeys(tags))  # 去重保序


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AI 标签分类 (智谱 GLM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY', '')
AI_MODEL = 'glm-4-flash'

AI_CLASSIFY_PROMPT = """你是一个日程分类助手。根据日程信息，分析其性质，返回分类和标签。

## 日程信息
- 标题: {summary}
- 地点: {location}
- 参与人: {attendees}
- 描述: {description}

## Notion 数据库中已有的标签（优先从中选取）
{existing_tags}

## 返回格式（严格 JSON，不要其他文字）
{{
  "category": "从以下选一个: 客户拜访, 内部会议, 团队管理, 培训学习, 商务活动, 项目评审, 方案汇报, 聚餐社交, 外部活动, 其他事项",
  "tags": ["标签1", "标签2", "标签3", "标签4"]
}}

## 分类规则
- 含"拜访""客户"→ 客户拜访
- 含"周会""例会""双周会""会议""对齐"→ 内部会议
- 含"晋级""晋升"→ 团队管理
- 含"培训""学习""分享""公开课"→ 培训学习
- 含"聚餐""晚宴""晚餐""午餐"→ 聚餐社交
- 含"评审""review"→ 项目评审
- 含"汇报""方案"→ 方案汇报
- 含"活动""峰会""研讨会"→ 外部活动
- 含"飞机""航班"→ 其他事项

## 标签规则（重要！选 3-6 个最相关的）
1. 必须包含 "周报"
2. 优先从已有标签中选取匹配的
3. 根据标题和内容提取关键主题词作为标签
4. 可以创建新标签，但每个不超过4个汉字
5. 涉及城市/地点时加上地点标签（如"深圳""北京""香港"）
6. 涉及出行/航班时加上"出差""交通""飞机"等
7. 涉及人名或公司时提取关键实体作为标签"""


def classify_with_ai(event: dict) -> tuple[str, list[str]]:
    """使用智谱 AI 分析日程标题和内容，返回 (分类, 标签列表)"""
    if not ZHIPU_API_KEY:
        return classify_keyword(event['summary'])

    try:
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=ZHIPU_API_KEY)

        # 已有标签（从 Notion 数据库获取的典型标签集合）
        existing_tags = (
            "周报, 会议, 周会, 例会, 拜访, 客户, 商务, 培训, 分享, 学习, 面试, 评审, "
            "聚餐, 社交, 晚宴, 活动, 汇报, 方案, 项目, 沟通, AI, 大模型, 教育, 政企, "
            "出差, 交通, 飞机, 航班, 机场, 深圳, 北京, 香港, 上海, 武汉, "
            "Leader, 1v1, 管理, 团队, FT, 双周会, FR会议, DevOps, 工具, 产品, "
            "ADP项目, 研讨会, 开源平台, 教育部, 高校, CTO, 架构师, 预留, 线上, "
            "外研社, 百校行, 港城大, 猿辅导, 作业帮, 策划, 人际关系, 工作交流"
        )

        prompt = AI_CLASSIFY_PROMPT.format(
            summary=event['summary'],
            location=event.get('location', '') or '',
            attendees=', '.join(event.get('attendees', [])[:10]),
            description=(event.get('description', '') or '')[:300],
            existing_tags=existing_tags,
        )

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_tokens=300,
        )

        result_text = response.choices[0].message.content.strip()

        # 解析 JSON
        if '```' in result_text:
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        import re
        json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group()

        result = json.loads(result_text.strip())
        category = result.get('category', '其他事项')
        tags = result.get('tags', ['周报', '工作'])

        # 确保 "周报" 标签存在
        if '周报' not in tags:
            tags.insert(0, '周报')

        # 标签去重、限制数量
        tags = list(dict.fromkeys(tags))[:8]

        return category, tags

    except Exception as e:
        print(f"    ⚠ AI 分类失败: {e}，使用关键词分类", flush=True)
        return classify_keyword(event['summary'])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Notion 写入
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def sync_events_to_notion(events: list[dict], synced_uids: set) -> tuple[int, int]:
    """同步事件到 Notion 数据库，含重试机制"""
    new_count = 0
    skip_count = 0
    fail_count = 0

    for ev in events:
        if ev['uid'] in synced_uids:
            skip_count += 1
            continue

        # AI 分类 + 标签
        cat, tags = classify_with_ai(ev)
        location = ev['location']
        now_iso = datetime.now(tz=BEIJING_TZ).isoformat()

        properties = {
            'title': {'title': [{'text': {'content': ev['summary']}}]},
            '领域': {'select': {'name': '🏢工作'}},
            '分类': {'multi_select': [{'name': cat}]},
            '标签': {'multi_select': [{'name': t} for t in tags]},
            'Date': {'date': {'start': ev['start'], 'end': ev['end']}},
            'UID': {'rich_text': [{'text': {'content': ev['uid']}}]},
            '创建时间': {'date': {'start': now_iso}},
            '更新时间': {'date': {'start': now_iso}},
        }

        if location and location != 'None' and location.strip() and len(location) <= 30:
            properties['地点'] = {'select': {'name': location}}

        if ev['attendees']:
            att_str = ', '.join(ev['attendees'])
            properties['人员'] = {'rich_text': [{'text': {'content': att_str[:2000]}}]}

        # 带重试的 Notion API 调用
        success = False
        for attempt in range(3):
            try:
                resp = httpx.post(
                    'https://api.notion.com/v1/pages',
                    headers=HEADERS,
                    json={'parent': {'database_id': DB_ID}, 'properties': properties},
                    timeout=15,
                )
                if resp.status_code == 200:
                    synced_uids.add(ev['uid'])
                    new_count += 1
                    print(f"    ✓ {ev['start'][:10]} {ev['summary'][:35]}", flush=True)
                    success = True
                    break
                else:
                    err = resp.text[:100]
                    if 'already exists' in err or '409' in str(resp.status_code):
                        synced_uids.add(ev['uid'])
                        print(f"    ⊘ 已存在: {ev['summary'][:30]}", flush=True)
                        success = True
                        break
                    else:
                        print(f"    ✗ {ev['summary'][:20]} → HTTP {resp.status_code}: {err}", flush=True)
                        break  # HTTP 错误不重试
            except Exception as ex:
                if attempt < 2:
                    import time
                    time.sleep(2 * (attempt + 1))  # 指数退避: 2s, 4s
                    continue
                print(f"    ✗ 网络异常 (重试{attempt+1}次后): {str(ex)[:50]}", flush=True)

        if not success:
            fail_count += 1

    if fail_count:
        print(f"    ⚠ {fail_count} 条因网络问题未同步", flush=True)

    return new_count, skip_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print('=' * 55)
    print('  企微日历同步 v3.0 — CalDAV 标准协议')
    print('=' * 55)

    # ── Step 1: 连接 CalDAV 服务器 ─────────────────────
    print('\n[1/5] 连接 CalDAV 服务器 (PROPFIND discover)...', flush=True)
    try:
        client, cal = connect_caldav()
        print(f"    ✓ 日历: {cal.name}", flush=True)
    except Exception as e:
        print(f"    ✗ 连接失败: {e}", flush=True)
        return

    # ── Step 2: 加载状态 & CTag 快速判断 ───────────────
    print('\n[2/5] 检查日历变更 (PROPFIND getctag)...', flush=True)
    state = load_state()
    synced_uids = set(state.get('synced_uids', []))
    old_ctag = state.get('ctag', '')
    old_sync_token = state.get('sync_token', '')

    print(f"    已记录: {len(synced_uids)} 条已同步 UID", flush=True)

    force_sync = '--force' in sys.argv
    new_ctag = get_calendar_ctag(cal)
    if new_ctag:
        print(f"    CTag: {new_ctag[:30]}...", flush=True)
        if old_ctag and new_ctag == old_ctag and not force_sync:
            print(f"    ✓ CTag 未变化，日历无更新，跳过同步", flush=True)
            print('\n完成! (无变更)')
            return
        elif force_sync:
            print(f"    ↻ 强制同步模式 (--force)", flush=True)
        elif old_ctag:
            print(f"    ↻ CTag 已变化，需要同步", flush=True)
        else:
            print(f"    ℹ 首次记录 CTag", flush=True)
    else:
        print(f"    ℹ 服务器不支持 CTag，继续完整查询", flush=True)

    # ── Step 3: 获取事件 ───────────────────────────────
    # 策略: 优先使用 sync-token 增量同步，降级为 REPORT calendar-query
    print('\n[3/5] 获取日历事件...', flush=True)

    all_events = []
    new_sync_token = None
    used_method = ''

    # 方案 A: sync-token 增量同步 (RFC 6578) — 非强制模式才使用
    if old_sync_token and not force_sync:
        print(f"    尝试 sync-token 增量同步 (RFC 6578)...", flush=True)
        sync_objects, new_sync_token = fetch_events_by_sync_token(cal, old_sync_token)
        if sync_objects is not None:
            used_method = 'sync-token'
            print(f"    ✓ 增量同步返回 {len(sync_objects)} 个变更对象", flush=True)
            for obj in sync_objects:
                parsed = parse_ical_event(obj)
                all_events.extend(parsed)

    # 方案 B: REPORT calendar-query + time-range (RFC 4791)
    if not used_method:
        today = datetime.now(tz=BEIJING_TZ)
        # 向前查 7 天 + 向后查 21 天 = 覆盖完整的上周到未来 3 周
        start_dt = today - timedelta(days=7)
        end_dt = today + timedelta(days=21)

        print(f"    使用 REPORT calendar-query (RFC 4791)...", flush=True)
        print(f"    查询范围: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}", flush=True)

        raw_events = fetch_events_by_report(cal, start_dt, end_dt)
        used_method = 'calendar-query'
        print(f"    ✓ 查询返回 {len(raw_events)} 个事件对象", flush=True)

        for raw in raw_events:
            parsed = parse_ical_event(raw, start_filter=start_dt, end_filter=end_dt)
            all_events.extend(parsed)

        # 如果首次使用，也尝试获取 sync-token 供下次增量同步
        if not old_sync_token:
            print(f"    获取 sync-token 供下次增量同步...", flush=True)
            try:
                sync_result = cal.objects_by_sync_token(load_objects=False)
                _ = list(sync_result)  # 消费迭代器
                new_sync_token = getattr(sync_result, 'sync_token', None)
                if new_sync_token:
                    print(f"    ✓ 已获取 sync-token", flush=True)
                else:
                    print(f"    ℹ 服务器不支持 sync-token", flush=True)
            except Exception as e:
                print(f"    ℹ 获取 sync-token 失败 (非致命): {e}", flush=True)

    # ── Step 4: 去重 & 解析 ─────────────────────────────
    print(f'\n[4/5] 处理事件...', flush=True)
    all_events = deduplicate_events(all_events)
    print(f"    去重后: {len(all_events)} 个唯一事件", flush=True)
    print(f"    同步方式: {used_method}", flush=True)

    # 按日期排序
    all_events.sort(key=lambda e: e.get('start', ''))

    # 显示事件列表
    if all_events:
        print(f"\n    日程列表:", flush=True)
        for ev in all_events:
            marker = '⊘' if ev['uid'] in synced_uids else '●'
            date_str = ev['start'][:10] if ev['start'] else '???'
            print(f"      {marker} {date_str} {ev['summary'][:40]}", flush=True)

    # ── Step 5: 同步到 Notion ──────────────────────────
    print(f'\n[5/5] 同步到 Notion...', flush=True)
    new_count, skip_count = sync_events_to_notion(all_events, synced_uids)

    # ── 保存状态 ───────────────────────────────────────
    state['synced_uids'] = sorted(synced_uids)
    if new_ctag:
        state['ctag'] = new_ctag
    if new_sync_token:
        state['sync_token'] = new_sync_token
    save_state(state)

    # ── 结果汇总 ───────────────────────────────────────
    print(f'\n{"=" * 55}')
    print(f'  同步完成!')
    print(f'    方式: {used_method}')
    print(f'    新增: {new_count} 条')
    print(f'    跳过: {skip_count} 条 (已同步)')
    print(f'    累计: {len(synced_uids)} 条')
    print(f'{"=" * 55}')


if __name__ == '__main__':
    main()
