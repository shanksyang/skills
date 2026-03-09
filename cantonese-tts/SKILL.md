---
name: cantonese-tts
description: "普通话转粤语语音工具。This skill should be used when users need to convert Mandarin Chinese text to Cantonese text and speech, generate Cantonese TTS audio, translate between Mandarin and Cantonese dialects. Covers Mandarin-to-Cantonese translation via LLM, Cantonese text-to-speech synthesis with multiple TTS engines, translation quality evaluation."
---

# 普通话转粤语语音工具

插件化架构的普通话→粤语翻译与语音合成引擎，支持多种 AI 翻译模型和 TTS 引擎的灵活组合。

## 概述

核心工作流：普通话文本 → 粤语文本 → 粤语语音

```
普通话文本输入
       ↓
  AI 翻译 (智谱AI/OpenAI/通义千问)
       ↓
  粤语文本
       ↓
  TTS 语音合成 (Edge-TTS/腾讯云TTS/gTTS)
       ↓
  粤语语音文件 (MP3/WAV)
```

### 支持的插件

| 层级 | 可选项 | 配置键 |
|------|--------|--------|
| AI 翻译 | 智谱 AI (glm-4-flash)、OpenAI（含 DeepSeek 等兼容接口）、通义千问 | `translator.type` |
| TTS 引擎 | Edge-TTS（免费）、腾讯云语音合成、gTTS（Google 免费） | `tts.type` |

### TTS 引擎对比

| 引擎 | 费用 | 粤语音色 | 质量 | 特点 |
|------|------|----------|------|------|
| Edge-TTS | 免费 | zh-HK-HiuGaaiNeural (女)、zh-HK-HiuMaanNeural (女)、zh-HK-WanLungNeural (男) | ★★★★ | 无需 API Key，微软 Edge 引擎 |
| 腾讯云 TTS | 按量计费 | 101019 智彤（粤语女声） | ★★★★★ | 专业粤语音色，需腾讯云账号 |
| gTTS | 免费 | Google Translate 粤语 | ★★★ | 简单免费，需要网络访问 Google |

## 使用场景

- 用户需要将普通话文本翻译成粤语
- 用户提到"粤语"、"广东话"、"Cantonese"、"粤语翻译"、"粤语语音"
- 用户需要粤语语音合成 / TTS
- 用户希望朗读粤语文本
- 用户需要评估不同翻译和 TTS 方案的效果

## 脚本

### `scripts/cantonese_tts_cli.py`

主 CLI 入口，可直接执行。

**命令：**
```bash
# 翻译并合成语音（默认使用 edge-tts）
python3 scripts/cantonese_tts_cli.py --text "你好，今天天气怎么样？"

# 仅翻译，不合成语音
python3 scripts/cantonese_tts_cli.py --text "今天开会讨论项目进度" --translate-only

# 指定翻译器和 TTS 引擎
python3 scripts/cantonese_tts_cli.py --text "我想学粤语" --translator zhipu --tts edge

# 使用腾讯云 TTS
python3 scripts/cantonese_tts_cli.py --text "明天见" --tts tencent

# 从文件读取输入
python3 scripts/cantonese_tts_cli.py --file input.txt --output output.mp3

# 指定配置文件
python3 scripts/cantonese_tts_cli.py --config cantonese_tts.yaml --text "测试"

# 运行效果评测
python3 scripts/cantonese_tts_cli.py --evaluate
```

**核心特性：**
- 支持 3 种 AI 翻译模型（智谱 AI / OpenAI / 通义千问）
- 支持 3 种 TTS 引擎（Edge-TTS / 腾讯云 / gTTS）
- 内置翻译质量评测，自动对比多个模型效果
- 内置 TTS 效果评测，生成不同引擎的对比音频
- 通过 YAML 配置文件灵活组合插件
- 支持 `${ENV_VAR}` 语法引用环境变量

### `scripts/setup_cantonese_tts.sh`

项目初始化脚本：
```bash
bash scripts/setup_cantonese_tts.sh /path/to/new/project
```

创建：核心模块、配置模板、`.env.example`、`requirements.txt`、`.gitignore`。

## 参考文档

### `references/environment_setup.md`

帮助用户配置环境变量、安装依赖或排查连接问题时阅读。包含：
- YAML 配置文件和 .env 两种配置方式
- 各翻译模型、TTS 引擎的凭据获取方式
- Python 依赖版本说明
- 验证命令

### `references/tts_engines.md`

理解 TTS 引擎选择或排查语音合成问题时阅读。包含：
- 三种 TTS 引擎详细对比
- 粤语音色完整列表
- 各引擎的 API 调用限制
- 音频格式和质量参数说明

## 资源文件

### `assets/config/cantonese_tts.example.yaml`

完整的配置文件模板，包含所有插件的配置示例。复制到项目根目录使用。

### `assets/config/evaluation_sentences.yaml`

翻译和 TTS 评测用的标准测试语句集。

## 工作流：搭建新项目

1. 运行 `scripts/setup_cantonese_tts.sh` 初始化项目结构
2. 阅读 `references/environment_setup.md` 了解配置说明
3. 编辑 `cantonese_tts.yaml` 选择翻译模型和 TTS 引擎
4. 在 `.env` 中填写凭据
5. `pip install -r requirements.txt` 安装依赖
6. `python3 cantonese_tts_cli.py --text "测试" --translate-only` 测试翻译
7. `python3 cantonese_tts_cli.py --text "测试"` 测试完整流程
8. `python3 cantonese_tts_cli.py --evaluate` 运行效果评测

## 工作流：常见组合配置

### 智谱 AI + Edge-TTS（推荐免费组合）
```yaml
translator: { type: zhipu, api_key: ${ZHIPU_API_KEY}, model: glm-4-flash }
tts: { type: edge, voice: zh-HK-HiuGaaiNeural }
```

### OpenAI + 腾讯云 TTS（高质量组合）
```yaml
translator: { type: openai, api_key: ${OPENAI_API_KEY}, model: gpt-4o-mini }
tts: { type: tencent, secret_id: ${TENCENT_SECRET_ID}, secret_key: ${TENCENT_SECRET_KEY}, voice_type: 101019 }
```

### 通义千问 + gTTS（全免费组合）
```yaml
translator: { type: qwen, api_key: ${DASHSCOPE_API_KEY}, model: qwen-turbo }
tts: { type: gtts }
```

## 工作流：问题排查

| 问题 | 解决方案 |
|------|----------|
| 翻译结果不准确 | 尝试不同模型，运行 `--evaluate` 对比效果 |
| Edge-TTS 连接失败 | 检查网络连接，Edge-TTS 使用 WebSocket 协议 |
| 腾讯云报错 | 检查 SecretId/SecretKey 权限，确认开通语音合成服务 |
| gTTS 无法使用 | 需要能访问 Google 服务的网络环境 |
| 音频文件为空 | 检查粤语文本是否正确，部分 TTS 不支持特殊字符 |
| 翻译器不可用 | 检查 API Key 是否有效，额度是否充足 |

## 关键技术细节

- **Edge-TTS**：使用 WebSocket 协议连接 Microsoft Edge 在线服务，无需 API Key
- **腾讯云 TTS**：VoiceType 101019（智彤）是唯一的粤语专用音色，PrimaryLanguage=1
- **gTTS**：使用 Google Translate TTS 接口，语言代码为 `zh-TW`（近似粤语）或 `zh-yue`
- **翻译 Prompt**：使用专门优化的粤语翻译提示词，要求输出地道粤语口语表达
- **OpenAI 兼容接口**：通过 `base_url` 支持 DeepSeek、通义千问等兼容 API
- **评测系统**：内置标准测试语句，支持 BLEU 评分和人工对照评估
