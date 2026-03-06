#!/bin/bash
# 文件上传工具 - 项目初始化脚本
# 用法: bash setup_file_upload.sh /path/to/project

set -e

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "Notion 文件上传工具 - 项目初始化"
echo "=================================================="
echo ""
echo "目标目录: $TARGET_DIR"
echo ""

# 创建目录结构
mkdir -p "$TARGET_DIR/config"
mkdir -p "$TARGET_DIR/uploads"

# 复制上传脚本
if [ -f "$SCRIPT_DIR/upload_to_notion.py" ]; then
    cp "$SCRIPT_DIR/upload_to_notion.py" "$TARGET_DIR/upload_to_notion.py"
    echo "✓ 已复制 upload_to_notion.py"
fi

# 复制分类配置
if [ -f "$SKILL_DIR/assets/config/file_categories.yaml" ]; then
    cp "$SKILL_DIR/assets/config/file_categories.yaml" "$TARGET_DIR/config/file_categories.yaml"
    echo "✓ 已复制 config/file_categories.yaml"
fi

# 创建 .env.example
cat > "$TARGET_DIR/.env.example" << 'EOF'
# Notion 配置
NOTION_TOKEN=your_notion_integration_token_here
NOTION_DATABASE_ID=your_database_id_here
EOF
echo "✓ 已创建 .env.example"

# 创建 requirements.txt（如果不存在）
if [ ! -f "$TARGET_DIR/requirements.txt" ]; then
    cat > "$TARGET_DIR/requirements.txt" << 'EOF'
notion-client==2.2.1
python-dotenv>=1.0.0
pyyaml>=6.0
EOF
    echo "✓ 已创建 requirements.txt"
else
    echo "⊘ requirements.txt 已存在（跳过）"
fi

# 创建 .gitignore（追加）
GITIGNORE="$TARGET_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q "upload_history.json" "$GITIGNORE" 2>/dev/null; then
        echo "" >> "$GITIGNORE"
        echo "# 文件上传历史" >> "$GITIGNORE"
        echo "upload_history.json" >> "$GITIGNORE"
        echo "uploads/" >> "$GITIGNORE"
        echo "✓ 已更新 .gitignore"
    fi
else
    cat > "$GITIGNORE" << 'EOF'
.env
__pycache__/
*.pyc
upload_history.json
uploads/
EOF
    echo "✓ 已创建 .gitignore"
fi

echo ""
echo "=================================================="
echo "初始化完成！"
echo ""
echo "下一步："
echo "  1. cp .env.example .env"
echo "  2. 编辑 .env 填写 NOTION_TOKEN 和 NOTION_DATABASE_ID"
echo "  3. pip install -r requirements.txt"
echo "  4. python3 upload_to_notion.py --list-categories"
echo "  5. python3 upload_to_notion.py --file /path/to/file --category '工作项目'"
echo "=================================================="
