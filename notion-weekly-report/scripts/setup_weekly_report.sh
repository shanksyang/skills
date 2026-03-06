#!/bin/bash
# Notion 周报生成器 - 项目初始化脚本
# 用法: bash setup_weekly_report.sh [目标目录]

set -e

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "  Notion 周报生成器 - 项目初始化"
echo "============================================================"
echo ""
echo "目标目录: $TARGET_DIR"
echo ""

# 创建目录结构
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# 复制脚本文件
echo "→ 复制核心脚本..."
cp "$SKILL_DIR/scripts/simple_report_generator.py" .

# 复制配置资源
echo "→ 复制配置文件..."
mkdir -p config
if [ -d "$SKILL_DIR/assets/config" ]; then
    cp "$SKILL_DIR/assets/config/"*.yaml config/ 2>/dev/null || true
fi

# 创建 .env 模板
if [ ! -f .env ]; then
    echo "→ 创建 .env 模板..."
    cat > .env.example << 'EOF'
# Notion 配置
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# 智谱 AI 配置
ZHIPU_API_KEY=your_zhipu_api_key

# 周报配置
WEEKLY_REPORT_AUTHOR=your_name
EOF
    echo "  ⚠ 请复制 .env.example 为 .env 并填写实际值"
fi

# 创建 requirements.txt
echo "→ 创建 requirements.txt..."
cat > requirements.txt << 'EOF'
notion-client==2.2.1
python-dotenv==1.0.0
zhipuai>=2.1.0
EOF

# 创建 .gitignore
if [ ! -f .gitignore ]; then
    echo "→ 创建 .gitignore..."
    cat > .gitignore << 'EOF'
.env
__pycache__/
*.pyc
reports/
EOF
fi

# 创建 reports 目录
mkdir -p reports

echo ""
echo "============================================================"
echo "  初始化完成!"
echo "============================================================"
echo ""
echo "后续步骤:"
echo "  1. cp .env.example .env  # 复制环境变量模板"
echo "  2. vim .env              # 填写 Notion Token、数据库 ID、智谱 API Key"
echo "  3. pip install -r requirements.txt  # 安装依赖"
echo "  4. python3 simple_report_generator.py this  # 生成本周周报"
echo ""
