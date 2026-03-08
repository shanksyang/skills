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
            today = datetime.now()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
        elif week_id.startswith("last "):
            weeks = int(week_id.split()[1])
            today = datetime.now()
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            start_date = this_monday - timedelta(weeks=weeks)
            end_date = this_monday + timedelta(days=6)
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

            # 统一为 naive datetime 进行比较
            if note_date and note_date.tzinfo is not None:
                note_date = note_date.replace(tzinfo=None)
            if note_date and start_date <= note_date <= end_date:
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

                filtered_notes.append({
                    "title": title,
                    "date": note_date,
                    "content": content,
                    "notion_categories": notion_categories,
                })

        print(f"✓ 获取到 {len(filtered_notes)} 篇笔记")
        return filtered_notes
    
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
            
            # 优先使用 Notion 分类属性映射（结合标题判断差旅）
            category = self._map_notion_category(notion_cats, title)
            if not category:
                category = self._classify_note(title, content)
            summary = self._summarize_note(title, content)
            
            if category not in categories:
                category = "其他事项"
            
            categories[category].append({
                "title": title,
                "date": note["date"],
                "summary": summary,
            })
        
        return categories
    
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
        
        return self._generate_markdown(categorized, start_date, end_date)
    
    def _generate_markdown(self, categorized, start_date, end_date):
        lines = []
        
        lines.append(f"**{self.author}周报**\n")
        
        start_str = start_date.strftime("%m.%d")
        end_str = end_date.strftime("%m.%d")
        year = start_date.year
        
        lines.append(f"**{year}年第{start_date.isocalendar()[1]}周**（{start_str}-{end_str}）\n")
        
        total = sum(len(v) for v in categorized.values())
        lines.append("**一、本周总结**\n")
        lines.append(f"本周共{total}项工作活动。\n")
        
        # 按固定顺序输出分类，跳过空分类
        section_idx = 1
        section_order = ["客户拜访", "内部会议", "差旅行程", "其他事项"]
        
        for category in section_order:
            items = categorized.get(category, [])
            if not items:
                continue
            lines.append(f"**{section_idx}.{category}**（{len(items)}项）\n")
            section_idx += 1
            for item in items:
                date_str = item["date"].strftime("%m/%d")
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][item["date"].weekday()]
                lines.append(f"● {weekday}（{date_str}）{item['title']}")
                lines.append(f"  {item['summary']}\n")
        
        return "\n".join(lines)
    
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
