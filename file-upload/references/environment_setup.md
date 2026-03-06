# 环境配置指南

## 环境变量

在项目根目录创建 `.env` 文件：

```bash
# Notion 配置（必需）
NOTION_TOKEN=your_notion_integration_token_here
NOTION_DATABASE_ID=your_database_id_here
```

### 获取 Notion Token

1. 访问 https://www.notion.so/my-integrations
2. 点击 "New integration"
3. 填写名称（如 "File Upload"），选择工作区
4. 复制 "Internal Integration Secret"（以 `ntn_` 开头）
5. **重要**：确保 Integration 具有以下权限：
   - Read content
   - Update content
   - Insert content

### 获取 Database ID

1. 在 Notion 中打开目标数据库页面
2. 从 URL 中提取 Database ID：
   ```
   https://www.notion.so/workspace/DATABASE_ID?v=...
   ```
3. Database ID 是 32 位十六进制字符串

### 关联 Integration 到数据库

1. 打开目标数据库页面
2. 点击右上角 `...` → "Connections" → "Connect to"
3. 选择你创建的 Integration
4. **必须执行此步骤，否则 API 无法访问该数据库**

## Python 依赖

```bash
pip install notion-client==2.2.1 python-dotenv pyyaml
```

> **关键**：必须使用 `notion-client==2.2.1`（v2 版本），v3.x 有不兼容的 API 变更。

## 验证配置

```bash
# 测试 Notion 连接
python3 -c "
from notion_client import Client
from dotenv import load_dotenv
import os
load_dotenv()
client = Client(auth=os.getenv('NOTION_TOKEN'))
db = client.databases.retrieve(database_id=os.getenv('NOTION_DATABASE_ID'))
print(f'数据库: {db[\"title\"][0][\"plain_text\"]}')
print('连接成功！')
"
```
