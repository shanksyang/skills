# 环境配置指南

## 必需的环境变量

在项目根目录创建 `.env` 文件，包含以下配置：

### Notion 配置

```bash
NOTION_TOKEN=ntn_xxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**获取方式：**
1. 访问 https://www.notion.so/my-integrations 创建 Integration
2. 复制 Internal Integration Token 作为 `NOTION_TOKEN`
3. 在 Notion 数据库页面，点击右上角 `...` → `Copy link`，URL 中 `?v=` 前的部分即为数据库 ID
4. 在数据库页面将 Integration 添加为连接

### 智谱 AI 配置

```bash
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx
```

**获取方式：**
1. 访问 https://open.bigmodel.cn 注册账号
2. 在 API Keys 页面创建密钥
3. 使用模型：`glm-4-flash`（免费额度充足）

### 周报作者名

```bash
WEEKLY_REPORT_AUTHOR=shanks
```

## Python 依赖

```bash
pip install notion-client==2.2.1 python-dotenv zhipuai
```

### 依赖说明

| 包名 | 版本 | 用途 |
|------|------|------|
| notion-client | ==2.2.1 | Notion API 客户端（必须用 v2，v3 有破坏性变更） |
| python-dotenv | >=1.0.0 | .env 环境变量加载 |
| zhipuai | >=2.1.0 | 智谱 AI SDK（笔记总结） |

## 验证配置

```bash
# 生成本周周报
python3 simple_report_generator.py this

# 生成最近 2 周周报
python3 simple_report_generator.py last 2
```

## Notion 数据库要求

周报生成器要求 Notion 数据库包含以下属性：
- `领域`（select 类型）：需包含 `🏢工作` 选项
- `Date`（date 类型）：笔记日期，用于按周筛选
- `title`（title 类型）：页面标题
