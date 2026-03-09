#!/bin/bash
# 粤语翻译与语音合成 - 项目初始化脚本
# 用法: bash setup_cantonese_tts.sh /path/to/project

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}用法: bash $0 /path/to/project${NC}"
    exit 1
fi

PROJECT_DIR="$1"
echo -e "${GREEN}🚀 初始化粤语翻译与语音合成项目${NC}"
echo "   目标目录: $PROJECT_DIR"

# 创建目录结构
echo -e "\n${YELLOW}📁 创建目录结构...${NC}"
mkdir -p "$PROJECT_DIR"/{config,output}

# 复制核心模块
echo -e "${YELLOW}📦 复制核心模块...${NC}"
cp -r "$SCRIPT_DIR/cantonese_tts" "$PROJECT_DIR/"
cp "$SCRIPT_DIR/cantonese_tts_cli.py" "$PROJECT_DIR/"

# 复制配置模板
echo -e "${YELLOW}⚙️  复制配置模板...${NC}"
cp "$SKILL_DIR/assets/config/cantonese_tts.example.yaml" "$PROJECT_DIR/config/"
cp "$SKILL_DIR/assets/config/evaluation_sentences.yaml" "$PROJECT_DIR/config/"

# 生成 .env.example
echo -e "${YELLOW}🔑 生成 .env.example...${NC}"
cat > "$PROJECT_DIR/.env.example" << 'EOF'
# 粤语翻译与语音合成 - 环境变量配置

# === 翻译器 API Key（至少配置一个）===

# 智谱 AI (推荐，glm-4-flash 有免费额度)
# 获取方式: https://open.bigmodel.cn/ → API Keys
ZHIPU_API_KEY=

# OpenAI (含兼容接口)
# 获取方式: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# 通义千问
# 获取方式: https://dashscope.console.aliyun.com/apiKey
DASHSCOPE_API_KEY=

# === TTS 引擎凭据（Edge-TTS 和 gTTS 无需配置）===

# 腾讯云 TTS (可选)
# 获取方式: https://console.cloud.tencent.com/cam/capi
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
EOF

# 生成 requirements.txt
echo -e "${YELLOW}📋 生成 requirements.txt...${NC}"
cat > "$PROJECT_DIR/requirements.txt" << 'EOF'
# 核心依赖
python-dotenv>=1.0.0
pyyaml>=6.0

# Edge-TTS (推荐，免费)
edge-tts>=6.1.0

# 翻译器 SDK（至少安装一个）
zhipuai>=2.0.0           # 智谱 AI
# openai>=1.0.0          # OpenAI / 通义千问 / DeepSeek

# 可选 TTS 引擎
# gTTS>=2.3.0                           # Google TTS (免费)
# tencentcloud-sdk-python-tts>=3.0.0    # 腾讯云 TTS
EOF

# 生成 .gitignore
echo -e "${YELLOW}📄 生成 .gitignore...${NC}"
cat > "$PROJECT_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# 环境变量
.env
.env.*
!.env.example

# 输出文件
output/
*.mp3
*.wav

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo
EOF

# 完成
echo -e "\n${GREEN}✅ 项目初始化完成！${NC}"
echo ""
echo "下一步:"
echo "  1. cd $PROJECT_DIR"
echo "  2. cp .env.example .env  # 填写 API Key"
echo "  3. cp config/cantonese_tts.example.yaml cantonese_tts.yaml  # 编辑配置"
echo "  4. pip install -r requirements.txt"
echo "  5. python3 cantonese_tts_cli.py --text '你好' --translate-only  # 测试翻译"
echo "  6. python3 cantonese_tts_cli.py --text '你好'  # 完整流程"
echo "  7. python3 cantonese_tts_cli.py --evaluate  # 运行评测"
