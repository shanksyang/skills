# 环境配置指南

## 配置方式

支持两种配置方式，可混合使用：

### 方式一：YAML 配置文件

复制 `config/cantonese_tts.example.yaml` 到项目根目录为 `cantonese_tts.yaml`，按需修改。

### 方式二：环境变量

复制 `.env.example` 为 `.env`，填写 API Key。

**优先级**: YAML 配置 > 环境变量 > 默认值

## 翻译器凭据

### 智谱 AI（推荐）

1. 注册 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 进入 API Keys 页面创建密钥
3. 设置 `ZHIPU_API_KEY=your_key`
4. 推荐模型: `glm-4-flash`（有免费额度，速度快）

### OpenAI

1. 注册 [OpenAI Platform](https://platform.openai.com/)
2. 创建 API Key
3. 设置 `OPENAI_API_KEY=your_key`
4. 推荐模型: `gpt-4o-mini`

**兼容接口**: 通过 `base_url` 支持 DeepSeek、Moonshot 等兼容 OpenAI 格式的服务：
```yaml
translator:
  type: openai
  api_key: ${DEEPSEEK_API_KEY}
  model: deepseek-chat
  base_url: https://api.deepseek.com/v1
```

### 通义千问

1. 注册 [阿里云 DashScope](https://dashscope.console.aliyun.com/)
2. 获取 API Key
3. 设置 `DASHSCOPE_API_KEY=your_key`
4. 推荐模型: `qwen-turbo`

## TTS 引擎凭据

### Edge-TTS（推荐）

**无需任何凭据**，免费使用微软 Edge 在线 TTS 服务。

粤语可用音色:
| 音色 ID | 说明 |
|---------|------|
| `zh-HK-HiuGaaiNeural` | 粤语女声（活泼）|
| `zh-HK-HiuMaanNeural` | 粤语女声（温柔）|
| `zh-HK-WanLungNeural` | 粤语男声 |

### 腾讯云 TTS

1. 注册 [腾讯云](https://cloud.tencent.com/)
2. 开通 [语音合成服务](https://console.cloud.tencent.com/tts)
3. 获取 [API 密钥](https://console.cloud.tencent.com/cam/capi)
4. 设置 `TENCENT_SECRET_ID` 和 `TENCENT_SECRET_KEY`
5. 粤语音色: VoiceType `101019`（智彤，粤语女声）

### gTTS

**无需凭据**，但需要能访问 Google 服务的网络环境。

## Python 依赖

```bash
# 核心依赖（必装）
pip install python-dotenv pyyaml

# Edge-TTS（推荐）
pip install edge-tts

# 翻译器 SDK（至少一个）
pip install zhipuai    # 智谱 AI
pip install openai     # OpenAI / 通义千问 / DeepSeek

# 可选 TTS
pip install gTTS                          # Google TTS
pip install tencentcloud-sdk-python-tts   # 腾讯云 TTS
```

## 验证命令

```bash
# 列出可用插件
python3 cantonese_tts_cli.py --list-plugins

# 验证配置
python3 cantonese_tts_cli.py --validate

# 测试翻译
python3 cantonese_tts_cli.py --text "你好" --translate-only

# 测试完整流程
python3 cantonese_tts_cli.py --text "你好"

# 运行评测
python3 cantonese_tts_cli.py --evaluate
```
