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
from datetime import datetime, timedelta
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
        print("正在从Notion获取笔记...")
        all_pages = []
        has_more = True
        next_cursor = None

        while has_more:
            query_params = {
                "database_id": self.database_id,
                "filter": {
                    "property": "领域",
                    "select": {
                        "equals": "🏢工作"
                    }
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

                filtered_notes.append({"title": title, "date": note_date, "content": content})

        print(f"✓ 获取到 {len(filtered_notes)} 篇笔记")
        return filtered_notes
    
    def summarize_with_zhipu(self, content, title):
        try:
            prompt = f"请将以下笔记内容总结为不超过100字的摘要：\n\n标题：{title}\n内容：{content}\n\n要求：简洁明了，突出要点。"
            
            response = self.zhipu.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content
            return summary.strip()
        except Exception as e:
            print(f"  ⚠ AI总结失败: {e}")
            return content[:100]
    
    def generate_report(self, start_date, end_date):
        print("\n正在使用智谱AI生成周报...")
        notes = self.fetch_notes(start_date, end_date)
        
        if not notes:
            print("⚠ 指定日期范围内没有笔记")
            return ""
        
        notes.sort(key=lambda x: x["date"])
        
        categorized = {"客户对接": [], "业务活动": [], "生活记录": []}
        
        for note in notes:
            title = note["title"]
            content = note["content"]
            
            if "生活" in title or "聚餐" in title:
                category = "生活记录"
            elif "管理" in title or "例会" in title or "周会" in title:
                category = "业务活动"
            else:
                category = "客户对接"
            
            summary = self.summarize_with_zhipu(content, title)
            categorized[category].append({"title": title, "date": note["date"], "summary": summary})
        
        return self._generate_markdown(categorized, start_date, end_date)
    
    def _generate_markdown(self, categorized, start_date, end_date):
        lines = []
        
        lines.append(f"**{self.author}周报**\n")
        
        start_str = start_date.strftime("%m%d")
        end_str = end_date.strftime("%m%d")
        year = start_date.year
        if end_date.year != start_date.year:
            end_str = f"{end_date.year}.{end_str}"
        
        lines.append(f"**{year}年{start_date.strftime('%m')}月第{start_date.isocalendar()[1]}周**（{start_str}{end_str}）\n")
        lines.append("**1、本周总结**\n")
        lines.append(f"本周共{sum(len(v) for v in categorized.values())}项工作活动。\n")
        
        category_map = {
            "客户对接": "**1.1、客户对接**\n",
            "业务活动": "**1.2、业务活动**\n",
            "生活记录": "**2、生活记录**\n"
        }
        
        for category, items in categorized.items():
            if items:
                lines.append(category_map.get(category, category))
                for item in items:
                    date_str = item["date"].strftime("%m%d")
                    weekday = ["一", "二", "三", "四", "五", "六", "日"][item["date"].weekday()]
                    lines.append(f"● {weekday}（{date_str}）：{item['title']}\n")
                    lines.append(f"{item['summary']}\n")
        
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
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"\n✓ 周报已生成: {filename}")
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
