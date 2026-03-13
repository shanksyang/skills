#!/usr/bin/env python3
"""
简化版周报生成器 - 使用智谱AI

从 Notion 数据库读取工作笔记，使用 AI 总结后生成周报 Markdown 文件。

使用方式:
    python3 simple_report_generator.py this           # 本周
    python3 simple_report_generator.py last 1         # 上周
    python3 simple_report_generator.py last 4         # 最近4周
    python3 simple_report_generator.py 20260202       # 指定工作周

环境变量:
    NOTION_TOKEN           - Notion Integration Token
    NOTION_DATABASE_ID     - Notion 数据库 ID
    ZHIPU_API_KEY          - 智谱 AI API Key
    WEEKLY_REPORT_AUTHOR   - 周报作者名（默认: shanks）
"""
import sys
import os
from datetime import datetime, timedelta, timezone
from notion_client import Client
from dotenv import load_dotenv
import zhipuai

load_dotenv()

# 北京时间时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def _beijing_now() -> datetime:
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

class SimpleReportGenerator:
    def __init__(self):
        self.notion = Client(auth=os.getenv("NOTION_TOKEN"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.zhipu = zhipuai.ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))
        self.author = os.getenv("WEEKLY_REPORT_AUTHOR", "shanks")
        # 输出目录：项目根目录下的 reports/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.normpath(os.path.join(script_dir, "..", "..", "..", ".."))
        self.output_dir = os.path.join(project_root, "reports")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_date_range(self, week_id):
        week_id = week_id.strip().lower()
        
        if week_id == "this":
            today = _beijing_now()
            days_since_monday = today.weekday()
            start_date = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
        elif week_id.startswith("last "):
            weeks = int(week_id.split()[1])
            today = _beijing_now()
            days_since_monday = today.weekday()
            this_monday = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = this_monday - timedelta(weeks=weeks)
            end_date = (this_monday - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)  # 上周日
        elif week_id.isdigit() and len(week_id) == 8:
            year = int(week_id[:4])
            month = int(week_id[4:6])
            week_num = int(week_id[6:7])
            
            first_day = datetime(year, month, 1)
            days_since_monday = first_day.weekday()
            first_monday = first_day - timedelta(days=days_since_monday)
            if days_since_monday == 0:
                first_monday = first_day
            
            start_date = first_monday + timedelta(weeks=(week_num - 1) * 7)
            end_date = start_date + timedelta(days=6)
        else:
            raise ValueError(f"无效的周标识符: {week_id}")
        
        return start_date, end_date
    
    def fetch_notes(self, start_date, end_date):
        print("正在从Notion获取笔记（筛选标签=周报）...")
        all_pages = []
        has_more = True
        next_cursor = None

        while has_more:
            query_params = {
                "database_id": self.database_id,
                "filter": {
                    "and": [
                        {
                            "property": "领域",
                            "select": {"equals": "🏢工作"}
                        },
                        {
                            "property": "标签",
                            "multi_select": {"contains": "周报"}
                        }
                    ]
                }
            }
            if next_cursor:
                query_params["start_cursor"] = next_cursor
            response = self.notion.databases.query(**query_params)
            all_pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")

        filtered_notes = []
        for page in all_pages:
            props = page.get("properties", {})

            title = "无标题"
            title_prop = props.get("title", {})
            if not title_prop or title_prop.get("type") != "title":
                title_prop = props.get("Name", {})
            if title_prop and title_prop.get("type") == "title":
                title_parts = title_prop.get("title", [])
                if title_parts:
                    title = title_parts[0].get("text", {}).get("content", "无标题")

            note_date = None
            for field_name in ["Date", "时间", "time"]:
                if field_name in props:
                    date_prop = props[field_name]
                    if date_prop and isinstance(date_prop, dict):
                        date_data = date_prop.get("date")
                        if date_data and isinstance(date_data, dict):
                            date_str = date_data.get("start", "")
                            if date_str:
                                try:
                                    if date_str.endswith("Z"):
                                        date_str = date_str.replace("Z", "+00:00")
                                    note_date = datetime.fromisoformat(date_str)
                                    break
                                except Exception as e:
                                    print(f"  日期解析失败: {date_str}, {e}")
                                    pass

            # 统一转为北京时间进行比较
            if note_date and note_date.tzinfo is not None:
                note_date = note_date.astimezone(BEIJING_TZ)
            elif note_date and note_date.tzinfo is None:
                note_date = note_date.replace(tzinfo=BEIJING_TZ)
            # 确保 start_date/end_date 也有时区信息
            _start = start_date.replace(tzinfo=BEIJING_TZ) if start_date.tzinfo is None else start_date
            _end = end_date.replace(tzinfo=BEIJING_TZ) if end_date.tzinfo is None else end_date
            if note_date and _start <= note_date <= _end:
                content = ""
                try:
                    blocks = self.notion.blocks.children.list(block_id=page["id"])
                    for block in blocks.get("results", []):
                        block_type = block.get("type", "")
                        if block_type == "paragraph":
                            paragraph = block.get("paragraph", {})
                            rich_text = paragraph.get("rich_text", [])
                            for rt in rich_text:
                                if rt.get("type") == "text":
                                    content += rt.get("text", {}).get("content", "")
                except Exception as e:
                    print(f"  获取内容失败 ({title}): {e}")

                # 读取 Notion 中的分类属性
                notion_categories = []
                cat_prop = props.get("分类", {})
                if cat_prop and cat_prop.get("type") == "multi_select":
                    for opt in cat_prop.get("multi_select", []):
                        notion_categories.append(opt.get("name", ""))

                # 读取地点属性
                location = ""
                loc_prop = props.get("地点")
                if loc_prop and isinstance(loc_prop, dict) and loc_prop.get("type") == "select" and loc_prop.get("select"):
                    location = loc_prop.get("select", {}).get("name", "")

                # 读取客户属性
                customer = ""
                cust_prop = props.get("客户")
                if cust_prop and isinstance(cust_prop, dict) and cust_prop.get("type") == "select" and cust_prop.get("select"):
                    customer = cust_prop.get("select", {}).get("name", "")

                filtered_notes.append({
                    "title": title,
                    "date": note_date,
                    "content": content,
                    "notion_categories": notion_categories,
                    "location": location,
                    "customer": customer,
                })

        print(f"✓ 获取到 {len(filtered_notes)} 篇笔记")
        return filtered_notes
    
    def fetch_next_week_plans(self, current_end_date):
        """获取下周（当前周结束后的下一周）带周报标签的工作笔记作为下周计划"""
        next_monday = (current_end_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # 确保 next_monday 是周一
        while next_monday.weekday() != 0:
            next_monday += timedelta(days=1)
        next_sunday = (next_monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
        
        print(f"\n正在从Notion获取下周计划（{next_monday.strftime('%m/%d')}-{next_sunday.strftime('%m/%d')}）...")
        
        all_pages = []
        has_more = True
        next_cursor = None
        
        while has_more:
            query_params = {
                "database_id": self.database_id,
                "filter": {
                    "and": [
                        {"property": "领域", "select": {"equals": "🏢工作"}},
                        {"property": "标签", "multi_select": {"contains": "周报"}}
                    ]
                }
            }
            if next_cursor:
                query_params["start_cursor"] = next_cursor
            response = self.notion.databases.query(**query_params)
            all_pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")
        
        plans = []
        for page in all_pages:
            props = page.get("properties", {})
            
            title = "无标题"
            title_prop = props.get("title", {})
            if not title_prop or title_prop.get("type") != "title":
                title_prop = props.get("Name", {})
            if title_prop and title_prop.get("type") == "title":
                title_parts = title_prop.get("title", [])
                if title_parts:
                    title = title_parts[0].get("text", {}).get("content", "无标题")
            
            note_date = None
            for field_name in ["Date", "时间", "time"]:
                if field_name in props:
                    date_prop = props[field_name]
                    if date_prop and isinstance(date_prop, dict):
                        date_data = date_prop.get("date")
                        if date_data and isinstance(date_data, dict):
                            date_str = date_data.get("start", "")
                            if date_str:
                                try:
                                    if date_str.endswith("Z"):
                                        date_str = date_str.replace("Z", "+00:00")
                                    note_date = datetime.fromisoformat(date_str)
                                    break
                                except Exception:
                                    pass
            
            if note_date and note_date.tzinfo is not None:
                note_date = note_date.astimezone(BEIJING_TZ)
            elif note_date and note_date.tzinfo is None:
                note_date = note_date.replace(tzinfo=BEIJING_TZ)
            
            _nw_start = next_monday.replace(tzinfo=BEIJING_TZ) if next_monday.tzinfo is None else next_monday
            _nw_end = next_sunday.replace(tzinfo=BEIJING_TZ) if next_sunday.tzinfo is None else next_sunday
            if note_date and _nw_start <= note_date <= _nw_end:
                # 读取 Notion 分类
                notion_categories = []
                cat_prop = props.get("分类", {})
                if cat_prop and cat_prop.get("type") == "multi_select":
                    for opt in cat_prop.get("multi_select", []):
                        notion_categories.append(opt.get("name", ""))
                
                # 读取地点属性
                location = ""
                loc_prop = props.get("地点")
                if loc_prop and isinstance(loc_prop, dict) and loc_prop.get("type") == "select" and loc_prop.get("select"):
                    location = loc_prop.get("select", {}).get("name", "")

                # 读取客户属性
                customer = ""
                cust_prop = props.get("客户")
                if cust_prop and isinstance(cust_prop, dict) and cust_prop.get("type") == "select" and cust_prop.get("select"):
                    customer = cust_prop.get("select", {}).get("name", "")

                plans.append({
                    "title": title,
                    "date": note_date,
                    "notion_categories": notion_categories,
                    "location": location,
                    "customer": customer,
                })
        
        plans.sort(key=lambda x: x["date"])
        print(f"✓ 获取到 {len(plans)} 项下周计划")
        return plans, next_monday, next_sunday
    
    def classify_and_summarize(self, notes):
        """使用 AI 批量分类并总结笔记"""
        categories = {
            "客户拜访": [],
            "内部会议": [],
            "差旅行程": [],
            "其他事项": [],
        }
        
        for note in notes:
            title = note["title"]
            content = note["content"]
            notion_cats = note.get("notion_categories", [])
            location = note.get("location", "")
            customer = note.get("customer", "")
            
            # 优先使用 Notion 分类属性映射（结合标题判断差旅）
            category = self._map_notion_category(notion_cats, title)
            if not category:
                category = self._classify_note(title, content)
            summary = self._summarize_note_detailed(title, content)
            
            if category not in categories:
                category = "其他事项"
            
            # 构建标题：地点+客户+主题
            display_title = self._build_display_title(title, location, customer)
            
            categories[category].append({
                "title": display_title,
                "date": note["date"],
                "summary": summary,
                "location": location,
                "customer": customer,
            })
        
        return categories
    
    def _build_display_title(self, title, location, customer):
        """构建显示标题：【地点】【客户名】【主题】"""
        parts = []
        if location:
            parts.append(f"【{location}】")
        if customer:
            parts.append(f"【{customer}】")
        parts.append(title)
        return "".join(parts)
    
    def _summarize_note_detailed(self, title, content):
        """AI 详细总结笔记（多句话）"""
        try:
            text = content if content.strip() else title
            prompt = (
                f"请将以下工作笔记总结为3-5句话的详细摘要（150-300字）。\n\n"
                f"标题：{title}\n内容：{text}\n\n"
                f"要求：\n"
                f"1. 详细描述工作内容、讨论要点、结论和决策（每条30-50字）\n"
                f"2. 必须忽略以下无关信息：日历同步、caldav、wecom、API、自动同步、企业微信日历、会议链接、电话号码、拨号方式、时区\n"
                f"3. 如果内容主要是行程信息（航班/酒店/交通），描述行程安排和目的\n"
                f"4. 如果内容为空或只有标题，根据标题推测事项并详细描述\n"
                f"5. 语言简洁专业，像写给领导看的周报风格\n"
                f"6. 使用中文句号分隔各句话"
            )
            
            response = self.zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=400,
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"  ⚠ AI详细总结失败: {e}")
            return content[:300] if content.strip() else title
    
    def _map_notion_category(self, notion_cats, title=""):
        """根据 Notion 分类属性 + 标题映射到周报分类"""
        if not notion_cats:
            return None
        
        # 差旅关键词优先判断（标题中含差旅关键词的 商务活动 归为差旅）
        travel_keywords = ["飞机", "航班", "酒店", "高铁", "火车", "打车", "机场", "车票", "住宿"]
        for kw in travel_keywords:
            if kw in title:
                return "差旅行程"
        
        cat_mapping = {
            "客户拜访": "客户拜访",
            "商务活动": "客户拜访",
            "方案汇报": "客户拜访",
            "内部会议": "内部会议",
            "会议": "内部会议",
            "项目评审": "内部会议",
            "培训学习": "内部会议",
            "团队管理": "内部会议",
            "管理": "内部会议",
            "聚餐社交": "其他事项",
            "聚餐": "其他事项",
            "活动": "其他事项",
        }
        
        for nc in notion_cats:
            if nc in cat_mapping:
                return cat_mapping[nc]
        return None
    
    def _classify_note(self, title, content):
        """AI 智能分类"""
        keywords_map = {
            "差旅行程": ["飞机", "航班", "酒店", "高铁", "火车", "打车", "机场", "车票"],
            "客户拜访": ["拜访", "客户", "briefing", "汇报", "对接"],
            "内部会议": ["例会", "周会", "评审", "分享", "周例会", "项目会", "kickoff"],
        }
        
        for category, keywords in keywords_map.items():
            for kw in keywords:
                if kw in title:
                    return category
        
        # 关键词未命中时用 AI 分类
        try:
            prompt = (
                f"请将以下工作事项分类为以下类别之一，只回复类别名称：\n"
                f"- 客户拜访（拜访客户、客户沟通、商务洽谈）\n"
                f"- 内部会议（公司内部会议、评审、分享）\n"
                f"- 差旅行程（机票、酒店、交通）\n"
                f"- 其他事项\n\n"
                f"标题：{title}\n内容摘要：{content[:200]}"
            )
            response = self.zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20,
            )
            result = response.choices[0].message.content.strip()
            for cat in ["客户拜访", "内部会议", "差旅行程", "其他事项"]:
                if cat in result:
                    return cat
        except Exception as e:
            print(f"  ⚠ AI分类失败: {e}")
        
        return "其他事项"
    
    def _summarize_note(self, title, content):
        """AI 总结笔记"""
        try:
            text = content if content.strip() else title
            prompt = (
                f"请将以下工作笔记总结为一句话摘要（不超过80字）。\n\n"
                f"标题：{title}\n内容：{text}\n\n"
                f"要求：\n"
                f"1. 只保留业务相关的关键信息（人物、事项、结论、决策）\n"
                f"2. 必须忽略以下无关信息：日历同步、caldav、wecom、API、自动同步、企业微信日历、会议链接、电话号码、拨号方式\n"
                f"3. 如果内容主要是行程信息（航班/酒店/交通），只保留出发地、目的地、时间\n"
                f"4. 如果内容为空或只有标题，根据标题推测事项并简要描述\n"
                f"5. 语言简洁专业，像写给领导看的周报"
            )
            
            response = self.zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150,
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"  ⚠ AI总结失败: {e}")
            return content[:100] if content.strip() else title
    
    def generate_report(self, start_date, end_date):
        print("\n正在使用智谱AI生成周报...")
        notes = self.fetch_notes(start_date, end_date)
        
        if not notes:
            print("⚠ 指定日期范围内没有笔记")
            return ""
        
        notes.sort(key=lambda x: x["date"])
        
        categorized = self.classify_and_summarize(notes)
        
        # 获取下周计划
        next_week_plans, nw_start, nw_end = self.fetch_next_week_plans(end_date)
        
        return self._generate_markdown(categorized, start_date, end_date, next_week_plans, nw_start, nw_end)
    
    def _generate_markdown(self, categorized, start_date, end_date, next_week_plans=None, nw_start=None, nw_end=None):
        lines = []
        
        lines.append(f"**{self.author}周报**\n")
        
        start_str = start_date.strftime("%m.%d")
        end_str = end_date.strftime("%m.%d")
        year = start_date.year
        
        lines.append(f"**{year}年第{start_date.isocalendar()[1]}周**（{start_str}-{end_str}）\n")
        
        # === 一、本周总结 ===
        total = sum(len(v) for v in categorized.values())
        
        # 统计各分类数量
        section_order = ["客户拜访", "内部会议", "差旅行程", "其他事项"]
        category_counts = {}
        for cat in section_order:
            category_counts[cat] = len(categorized.get(cat, []))
        
        # 汇总段落
        summary_parts = []
        for cat in section_order:
            count = category_counts.get(cat, 0)
            if count > 0:
                summary_parts.append(f"{cat}{count}项")
        summary_text = "、".join(summary_parts) if summary_parts else "无"
        
        lines.append("**一、本周总结**\n")
        lines.append(f"本周共 **{total}** 项工作活动，包括 {summary_text}。\n")
        
        # 按分类展开，标题+内容解析格式
        section_idx = 1
        for category in section_order:
            items = categorized.get(category, [])
            if not items:
                continue
            
            lines.append(f"\n**{section_idx}.{category}**（{len(items)}项）\n")
            section_idx += 1
            
            # 每个条目独立展示：时间，标题，客户 + AI总结
            for item in items:
                date_str = item["date"].strftime("%m/%d")
                time_str = item["date"].strftime("%H:%M") if item["date"].hour != 0 or item["date"].minute != 0 else ""
                title = item.get("title", "")
                customer = item.get("customer", "")
                
                # 构建头部信息（地点已在title中，无需重复）
                header_parts = [f"{date_str} {time_str}" if time_str else date_str, title]
                if customer:
                    header_parts.append(customer)
                
                header = "，".join(filter(None, header_parts))
                lines.append(f"- {header}")
                
                # AI 总结内容（差旅行程不需要）
                if category != "差旅行程":
                    summary = item.get("summary", "")
                    if summary:
                        # 换行缩进显示总结
                        for line in summary.split('\n'):
                            lines.append(f"  {line}")
                lines.append("")
        
        # === 二、下周计划 ===
        lines.append("\n**二、下周计划**\n")
        
        if next_week_plans and nw_start and nw_end:
            nw_start_str = nw_start.strftime("%m.%d")
            nw_end_str = nw_end.strftime("%m.%d")
            
            # 按分类汇总下周计划
            plan_categories = {}
            for plan in next_week_plans:
                category = self._map_notion_category(plan.get("notion_categories", []), plan["title"])
                if not category:
                    category = self._classify_note(plan["title"], "")
                if category not in plan_categories:
                    plan_categories[category] = []
                
                location = plan.get("location", "")
                customer = plan.get("customer", "")
                display_title = self._build_display_title(plan["title"], location, customer)
                
                plan_categories[category].append({
                    "title": display_title,
                    "date": plan["date"],
                    "location": location,
                    "customer": customer,
                })
            
            lines.append(f"下周（{nw_start_str}-{nw_end_str}）共 **{len(next_week_plans)}** 项计划：\n")
            
            # 每个条目独立展示
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            
            for cat in section_order:
                cat_plans = plan_categories.get(cat, [])
                if not cat_plans:
                    continue
                lines.append(f"\n**{cat}**（{len(cat_plans)}项）")
                
                for plan in cat_plans:
                    date_str = plan["date"].strftime("%m/%d")
                    weekday = weekday_names[plan["date"].weekday()]
                    title = plan["title"]
                    customer = plan["customer"]
                    
                    # 构建头部信息（地点已在title中）
                    header_parts = [f"{weekday} {date_str}", title]
                    if customer:
                        header_parts.append(customer)
                    
                    header = "，".join(filter(None, header_parts))
                    lines.append(f"- {header}")
                
                lines.append("")
        else:
            lines.append("暂无下周计划安排。\n")
        
        return "\n".join(lines)
    
    def _generate_category_summary(self, category, items):
        """使用 AI 生成单个分类的汇总段落"""
        # 提取所有事项的摘要
        summaries = []
        for item in items:
            date_str = item["date"].strftime("%m/%d")
            summaries.append(f"【{date_str}】{item['title']}：{item['summary']}")
        
        combined = "\n".join(summaries)
        
        try:
            prompt = (
                f"请将以下{len(items)}项{category}工作汇总成一段话（200-400字）。\n\n"
                f"要求：\n"
                f"1. 按时间顺序叙述本周的{category}工作\n"
                f"2. 合并相似内容，突出重点工作和关键成果\n"
                f"3. 提及重要的客户、地点、决策和后续行动\n"
                f"4. 语言简洁专业，像写给领导看的周报\n\n"
                f"原始内容：\n{combined}"
            )
            
            response = self.zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500,
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"  ⚠ AI分类汇总失败: {e}")
            # 降级处理：直接列出
            return combined
    
    def run(self, week_id):
        try:
            start_date, end_date = self.get_date_range(week_id)
            
            print("=" * 60)
            print("AI周报生成器")
            print("=" * 60)
            print(f"时间范围: {start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%m月%d日')}")
            print(f"使用AI引擎: 智谱AI")
            print("=" * 60)
            print()
            
            report = self.generate_report(start_date, end_date)
            
            if not report:
                return 1
            
            if week_id == "this":
                filename = f"周报_{start_date.strftime('%Y%m%d')}.md"
            elif week_id.startswith("last "):
                weeks = week_id.split()[1]
                filename = f"周报_最近{weeks}周_{start_date.strftime('%Y%m%d')}.md"
            else:
                filename = f"周报_{week_id}_{start_date.strftime('%Y%m%d')}.md"
            
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"\n✓ 周报已生成: {filepath}")
            print(f"  文件大小: {len(report)} 字符")
            
            print("\n" + "=" * 60)
            print("周报预览（前800字）:")
            print("=" * 60)
            print(report[:800])
            if len(report) > 800:
                print("...")
            print("=" * 60)
            
            return 0
            
        except Exception as e:
            print(f"\n✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    generator = SimpleReportGenerator()
    if len(sys.argv) > 1:
        week_id = " ".join(sys.argv[1:])
    else:
        week_id = "this"
    exit_code = generator.run(week_id)
    sys.exit(exit_code)
