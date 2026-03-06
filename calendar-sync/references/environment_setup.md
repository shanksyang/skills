# 环境配置指南

## 配置方式

通用日历同步工具支持两种配置方式：

1. **YAML 配置文件**（推荐）：`calendar_sync.yaml`
2. **环境变量**（向后兼容）：`.env` 文件

## 方式一：YAML 配置文件

复制 `calendar_sync.example.yaml` 为 `calendar_sync.yaml`，按需修改。

配置文件查找顺序：
1. `--config` 参数指定的路径
2. `calendar_sync.yaml`
3. `config/calendar_sync.yaml`
4. `.calendar_sync.yaml`

### 环境变量引用

YAML 中可使用 `${ENV_VAR}` 引用环境变量：
```yaml
source:
  password: ${WECOM_CALDAV_PASSWORD}
```

## 方式二：环境变量 (.env)

在项目根目录创建 `.env` 文件。工具会自动检测可用服务并选择：

### 日历源

#### 企业微信 CalDAV
```bash
WECOM_CALDAV_URL=https://caldav.wecom.work/calendar/
WECOM_CALDAV_USERNAME=yourname@company.com
WECOM_CALDAV_PASSWORD=xxxxxxxxxxxxxxxx
```
- URL 末尾的 `/calendar/` 不可省略
- 密码是动态的，过期需从手机端重新获取

#### Google Calendar
```bash
GOOGLE_CALENDAR_CREDENTIALS=credentials.json
```
- 需要在 Google Cloud Console 创建 OAuth2 凭据
- 首次运行会弹出浏览器授权

### AI 分类器

按优先级检测：智谱 > OpenAI > Claude > 关键词

#### 智谱 AI
```bash
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx
```
- 注册: https://open.bigmodel.cn
- 模型: `glm-4-flash`（免费额度充足）

#### OpenAI / 兼容接口
```bash
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```
- DeepSeek: `OPENAI_BASE_URL=https://api.deepseek.com/v1`
- 通义千问: `OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`

#### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

### 笔记输出

按优先级检测：Notion > Obsidian > Logseq

#### Notion
```bash
NOTION_TOKEN=ntn_xxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
- 创建 Integration: https://www.notion.so/my-integrations
- 必须使用 `notion-client==2.2.1`（v3 有破坏性变更）

#### Obsidian
```bash
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault
```

#### Logseq
```bash
LOGSEQ_GRAPH_PATH=/path/to/logseq/graph
```

## Python 依赖

```bash
# 核心（必装）
pip install python-dotenv pyyaml icalendar

# 按使用的插件安装
pip install caldav                    # CalDAV 日历源
pip install notion-client==2.2.1      # Notion 输出
pip install zhipuai                   # 智谱 AI
pip install openai                    # OpenAI / 兼容接口
pip install anthropic                 # Claude
```

### 依赖速查表

| 包名 | 用途 | 必须 |
|------|------|------|
| python-dotenv | .env 加载 | ✓ |
| pyyaml | 配置文件解析 | ✓ |
| icalendar | iCal 数据解析 | ✓ |
| caldav | CalDAV 日历源 | 按需 |
| notion-client==2.2.1 | Notion 输出 | 按需 |
| zhipuai | 智谱 AI | 按需 |
| openai | OpenAI | 按需 |
| anthropic | Claude | 按需 |
| google-api-python-client | Google Calendar | 按需 |
| msal | Outlook | 按需 |

## 验证配置

```bash
python3 calendar_sync_cli.py --validate         # 验证配置
python3 calendar_sync_cli.py --list-plugins      # 查看可用插件
python3 calendar_sync_cli.py --list-calendars    # 测试连接
python3 calendar_sync_cli.py --test              # 测试读取+分类
```
