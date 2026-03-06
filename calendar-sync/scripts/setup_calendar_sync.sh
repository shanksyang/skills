#!/bin/bash
# 通用日历同步工具 - 项目初始化脚本
# 用法: bash setup_calendar_sync.sh [目标目录]

set -e

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "  通用日历同步工具 - 项目初始化"
echo "============================================================"
echo ""
echo "目标目录: $TARGET_DIR"
echo ""

# 创建目录结构
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# 复制核心包
echo "→ 复制核心模块..."
cp -r "$SKILL_DIR/scripts/calendar_sync" .
cp "$SKILL_DIR/scripts/calendar_sync_cli.py" .

# 复制配置资源
echo "→ 复制配置文件..."
mkdir -p config
if [ -d "$SKILL_DIR/assets/config" ]; then
    cp "$SKILL_DIR/assets/config/"*.yaml config/ 2>/dev/null || true
fi

# 创建示例配置
if [ ! -f calendar_sync.yaml ]; then
    echo "→ 创建配置文件模板..."
    cp "$SKILL_DIR/assets/config/calendar_sync.example.yaml" calendar_sync.yaml
fi

# 创建 .env 模板
if [ ! -f .env ]; then
    echo "→ 创建 .env 模板..."
    cat > .env.example << 'EOF'
# ============================================================
# 日历源凭据（根据使用的日历源配置）
# ============================================================

# 企业微信 CalDAV
WECOM_CALDAV_URL=https://caldav.wecom.work/calendar/
WECOM_CALDAV_USERNAME=your_email@company.com
WECOM_CALDAV_PASSWORD=your_caldav_password

# ============================================================
# AI API Key（根据使用的 AI 模型配置，可选）
# ============================================================

# 智谱 AI
ZHIPU_API_KEY=your_zhipu_api_key

# OpenAI / 兼容接口
# OPENAI_API_KEY=your_openai_api_key
# OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic Claude
# ANTHROPIC_API_KEY=your_anthropic_api_key

# ============================================================
# 笔记应用凭据（根据使用的输出目标配置）
# ============================================================

# Notion
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Obsidian
# OBSIDIAN_VAULT_PATH=/path/to/vault

# Logseq
# LOGSEQ_GRAPH_PATH=/path/to/graph
EOF
    echo "  ⚠ 请复制 .env.example 为 .env 并填写实际值"
fi

# 创建 requirements.txt
echo "→ 创建 requirements.txt..."
cat > requirements.txt << 'EOF'
# 核心依赖
python-dotenv>=1.0.0
pyyaml>=6.0
icalendar>=5.0.0

# CalDAV 日历源
caldav>=1.3.0

# Notion 输出
notion-client==2.2.1

# AI 分类器（按需安装）
# zhipuai>=2.1.0            # 智谱 AI
# openai>=1.0.0             # OpenAI / 兼容接口
# anthropic>=0.20.0         # Claude
# requests                  # Ollama (已内置)

# Google Calendar 日历源（可选）
# google-api-python-client
# google-auth-httplib2
# google-auth-oauthlib

# Outlook 日历源（可选）
# msal
# requests
EOF

# 创建 .gitignore
if [ ! -f .gitignore ]; then
    echo "→ 创建 .gitignore..."
    cat > .gitignore << 'EOF'
.env
sync_state.json
__pycache__/
*.pyc
token.json
outlook_token.json
credentials.json
calendar_notes/
EOF
fi

echo ""
echo "============================================================"
echo "  初始化完成!"
echo "============================================================"
echo ""
echo "后续步骤:"
echo "  1. cp .env.example .env              # 复制环境变量模板"
echo "  2. vim .env                           # 填写凭据"
echo "  3. vim calendar_sync.yaml             # 配置日历源/AI/输出"
echo "  4. pip install -r requirements.txt    # 安装依赖"
echo "  5. python3 calendar_sync_cli.py --list-plugins     # 查看可用插件"
echo "  6. python3 calendar_sync_cli.py --validate         # 验证配置"
echo "  7. python3 calendar_sync_cli.py --list-calendars   # 列出日历"
echo "  8. python3 calendar_sync_cli.py --test             # 测试"
echo "  9. python3 calendar_sync_cli.py                    # 正式同步"
echo ""
