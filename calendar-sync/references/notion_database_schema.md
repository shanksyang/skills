# Notion 数据库 Schema

日历同步使用的 Notion 数据库属性定义。

## 属性列表

| 属性名 | 类型 | 说明 | 可选值/格式 |
|--------|------|------|-------------|
| `title` | title | 页面标题（日程名称） | 自由文本 |
| `Date` | date | 日期/时间 | ISO 8601 格式，支持 start + end |
| `领域` | select | 所属领域 | `🏢工作`, `🏠生活`, `📚学习` 等 |
| `分类` | multi_select | 内容分类 | `客户拜访`, `内部会议`, `团队管理`, `培训学习`, `商务活动`, `项目评审`, `方案汇报`, `聚餐社交` |
| `标签` | multi_select | 标签 | 自由标签，如 `工作`, `会议`, `周报`, `AI`, `客户` 等 |
| `创建时间` | date | 记录创建时间 | ISO 8601 格式，自动填充 |
| `更新时间` | date | 记录更新时间 | ISO 8601 格式，自动填充 |

## 字段名自定义

在 `calendar_sync.yaml` 中可自定义字段名：

```yaml
output:
  type: notion
  domain_field: "领域"      # 默认
  category_field: "分类"    # 默认
  tags_field: "标签"        # 默认
  date_field: "Date"        # 默认
  default_domain: "🏢工作"  # 默认
```

## 创建页面示例（Python）

```python
from notion_client import Client
from datetime import datetime, timedelta, timezone

client = Client(auth="your_token")
now_iso = datetime.now(tz=timezone(timedelta(hours=8))).isoformat()

client.pages.create(
    parent={"database_id": "your_db_id"},
    properties={
        "title": {"title": [{"text": {"content": "页面标题"}}]},
        "领域": {"select": {"name": "🏢工作"}},
        "Date": {"date": {"start": "2026-03-01T09:00:00", "end": "2026-03-01T10:00:00"}},
        "分类": {"multi_select": [{"name": "内部会议"}]},
        "标签": {"multi_select": [{"name": "工作"}, {"name": "会议"}, {"name": "周报"}]},
        "创建时间": {"date": {"start": now_iso}},
        "更新时间": {"date": {"start": now_iso}},
    },
    children=[
        # Notion block 内容
    ]
)
```

## 日历同步分类映射

| AI 分类 | event_type | 内容模板 |
|---------|------------|----------|
| 客户拜访 | visit | 拜访目的 → 沟通要点 → 客户反馈 → 后续跟进 |
| 内部会议 | meeting | 会议议题 → 会议纪要 → 待办事项 |
| 团队管理 | review | 评审内容 → 关键结论 → 后续行动 |
| 培训学习 | training | 学习主题 → 核心收获 → 实践计划 |
| 商务活动 | other | 详情 → 笔记 |
| 项目评审 | review | 评审内容 → 关键结论 → 后续行动 |
| 方案汇报 | report | 汇报主题 → 核心内容 → 决策结论 → 后续跟进 |
| 聚餐社交 | social | 活动记录 |
