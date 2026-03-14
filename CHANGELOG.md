# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/) 规范。

## 版本规划

### v1.1.0（计划中）
- [ ] 支持粤语→普通话反向翻译
- [ ] 支持批量文件翻译和合成
- [ ] 添加 OpenAI TTS 引擎（支持粤语）
- [ ] 添加阿里云 Qwen3-TTS 引擎
- [ ] Web UI 界面
- [ ] 支持实时流式语音合成

### v1.2.0（计划中）
- [ ] 粤语语音识别（ASR）支持
- [ ] 支持粤语方言细分（广州话、港式粤语、台山话等）
- [ ] 自定义翻译词典/术语表
- [ ] 语音克隆集成
- [ ] 多轮对话式粤语翻译

---

## [3.1.0] - 2026-03-15

### calendar-sync v3.1.0 — AI 智能标签分类 + 脚本精简

#### AI 智能标签分类
- **集成智谱 GLM AI**: sync_batch.py 新增 AI 标签分类，替代硬编码 `['周报']`
- **多维度标签生成**: AI 从标题/地点/参与人/描述自动分析生成 3-6 个标签（如：周报, 拜访, 客户, 猿辅导, 北京）
- **分类 + 标签双输出**: AI 同时输出分类（category）和标签（tags），分类更精准
- **关键词 fallback**: ZHIPU_API_KEY 未配置或 AI 调用失败时自动降级为增强版关键词分类
- **历史数据回填**: 生成脚本更新了 84 条已有 Notion 记录的标签（2026-03-08 ~ 2026-04-03）

#### 脚本精简
- **删除 `sync_simple.py`**: 功能已完全合并到 sync_batch.py
- **删除 `quick_sync.py`**: 功能已完全合并到 sync_batch.py
- **统一入口**: sync_batch.py 作为唯一推荐的独立同步脚本

## [3.0.0] - 2026-03-13

### calendar-sync v3.0.0 — 基于 CalDAV 标准协议重构
- **REPORT calendar-query** (RFC 4791): 一次请求获取整个时间范围的事件，取代旧版按天逐个查询的低效方式（15+ 次 HTTP → 1 次）
- **sync-token 增量同步** (RFC 6578): 通过 sync-collection REPORT 只拉取上次同步后变更的事件，大幅降低网络开销
- **CTag 快速检测**: 通过 PROPFIND getctag 判断日历是否有变更，无变更时零查询跳过
- **expand 循环事件**: 服务端展开 RRULE 循环规则，确保周期性会议不遗漏
- **ETag 变更检测**: 精确判断单个事件是否被修改
- **时间格式升级**: 定时事件使用 ISO 8601 完整时间格式（含时区），全天事件保持日期格式
- **优雅降级策略**: expand 不支持时自动退回基础查询，sync-token 不支持时自动使用 calendar-query
- **插件版同步更新**: caldav_source.py 同步使用标准协议，增加 expand + split_expanded 支持
- **所有脚本统一升级**: sync_batch.py 全面重构，删除 sync_simple.py 和 quick_sync.py

## [2.1.0] - 2026-03-13

### calendar-sync v2.1.0
- **新增属性**: Notion 数据库新增 `创建时间` 和 `更新时间` 属性（date 类型）
  - 创建页面时自动填充当前北京时间（UTC+8）
  - 所有同步脚本统一支持：sync_batch.py / sync_simple.py / quick_sync.py / notion_writer.py（插件版）
  - 字段名可通过配置文件自定义（`created_time_field` / `updated_time_field`）
- **更新文档**: 同步更新 Notion Schema 文档、SKILL.md、配置模板

## [1.0.0] - 2026-03-10

### 新增 Skills

#### cantonese-tts v1.0.0 - 普通话转粤语语音工具
- **翻译功能**: 支持 3 种 AI 翻译模型
  - 智谱 AI (glm-4-flash) - 推荐，有免费额度
  - OpenAI (GPT-4o-mini) - 含 DeepSeek 等兼容接口支持
  - 通义千问 (qwen-turbo) - 阿里云免费额度
- **语音合成**: 支持 3 种 TTS 引擎
  - Edge-TTS - 免费，3 种粤语音色（2 女 1 男）
  - 腾讯云 TTS - 专业粤语音色（智彤 101019）
  - gTTS - Google 免费 TTS
- **评测系统**: 内置翻译质量和 TTS 效果评测
  - 10 组标准测试语句，覆盖日常问候、购物、工作等场景
  - 粤语特征词评分 + 参考相似度评分
  - 多引擎对比评测，自动生成评测报告
- **插件化架构**: 翻译器和 TTS 引擎可灵活组合
  - 注册表模式，易于扩展新插件
  - YAML 配置 + 环境变量双重配置方式
- **CLI 工具**: 完整的命令行接口
  - `--text` 翻译并合成
  - `--translate-only` 仅翻译
  - `--evaluate` 运行评测
  - `--list-plugins` 查看可用插件
- **项目初始化脚本**: `setup_cantonese_tts.sh`
- **参考文档**: 环境配置指南、TTS 引擎对比文档

### 评测结果（v1.0.0）

| 模块 | 引擎 | 成功率 | 评分 |
|------|------|--------|------|
| 翻译 | 智谱 AI (glm-4-flash) | 10/10 | 粤语特征 0.57，相似度 0.75 |
| TTS | Edge-TTS | 5/5 | 平均合成 1.26s |

---

## 已有 Skills

### calendar-sync v3.1.0
通用日历同步工具，插件化架构，基于 CalDAV 标准协议 (RFC 4791/6578)，AI 智能标签分类。

### notion-weekly-report v1.1.0
Notion 笔记生成 AI 周报，支持总分结构+标题内容解析格式。

### file-upload v1.0.0
Notion 文件上传与管理工具。
