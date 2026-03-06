---
name: notion-weekly-report
description: "Notion 笔记生成 AI 周报工具。This skill should be used when users need to generate weekly reports from Notion notes using AI summarization, query Notion database for work notes, or automate weekly report generation. Covers Notion data querying, AI-powered note summarization, and formatted Markdown report output."
---

# Notion 笔记生成 AI 周报

从 Notion 数据库读取工作笔记，使用智谱 AI 智能总结，自动生成分类汇总的 Markdown 格式周报。

## 概述

核心工作流：Notion 工作笔记 → AI 智能总结 → Markdown 周报

```
Notion 数据库（工作笔记）
       ↓
  simple_report_generator.py
       ↓
  智谱 AI (glm-4-flash) → 笔记总结
       ↓
  周报 Markdown 文件
```

## 使用场景

- 用户需要从 Notion 笔记生成周报
- 用户需要自动汇总一段时间内的工作记录
- 用户提到"周报"、"生成周报"、"工作总结"、"周报生成"
- 用户希望 AI 帮忙总结笔记内容

## 脚本

### `scripts/simple_report_generator.py`

周报生成器，可直接执行。

**命令：**
```bash
# 本周周报
python3 scripts/simple_report_generator.py this

# 最近 N 周
python3 scripts/simple_report_generator.py last 4

# 指定工作周（YYYYMMWW 格式）
python3 scripts/simple_report_generator.py 20260202
```

**输出：** Markdown 文件 `周报_YYYYMMDD.md`，包含分类汇总。

**核心特性：**
- 自动查询 Notion 数据库中 `领域=🏢工作` 的笔记
- 按日期范围筛选笔记
- 使用智谱 AI 对每篇笔记生成摘要
- 自动分类为：客户对接、业务活动、生活记录
- 输出格式化 Markdown 周报，按日期排列

### `scripts/setup_weekly_report.sh`

项目初始化脚本，从零开始搭建周报生成项目时运行：
```bash
bash scripts/setup_weekly_report.sh /path/to/new/project
```

创建：周报脚本、配置目录、`.env.example`、`requirements.txt`、`.gitignore`。

## 参考文档

### `references/environment_setup.md`

帮助用户配置环境变量、安装依赖或排查问题时，请阅读此文件。包含：
- Notion、智谱 AI 环境变量及获取方式
- Python 依赖版本（关键：`notion-client==2.2.1`，不能用 v3）
- 验证命令

### `references/notion_database_schema.md`

理解 Notion 数据库结构或调试查询问题时，请阅读此文件。包含：
- 数据库属性 Schema
- 查询过滤条件说明
- 周报涉及的属性字段

## 资源文件

### `assets/config/ai_prompts.yaml`

AI 总结提示词模板，支持不同总结级别（简短/标准/详细）。复制到项目的 `config/` 目录使用。

## 工作流：搭建新项目

1. 运行 `scripts/setup_weekly_report.sh` 初始化项目结构
2. 阅读 `references/environment_setup.md` 了解配置说明
3. 帮助用户在 `.env` 中填写实际凭据
4. 确保 Notion 数据库中有工作笔记（`领域=🏢工作`，`Date` 属性已设置）
5. 生成周报：`python3 simple_report_generator.py this`

## 工作流：问题排查

| 问题 | 解决方案 |
|------|----------|
| Notion API 报错 | 确保使用 `notion-client==2.2.1`（v3 有破坏性变更），检查 Token 权限 |
| 周报为空 | 检查日期范围，确保 Notion 笔记设置了 `领域=🏢工作` 和 `Date` 属性 |
| AI 总结失败 | 检查 `ZHIPU_API_KEY` 是否正确，失败时自动截取前 100 字作为摘要 |
| 日期范围不对 | 使用 `this`（本周）、`last N`（最近 N 周）或 `YYYYMMWW`（指定周） |

## 关键技术细节

- **Notion API 版本**：必须使用 `notion-client==2.2.1`（Python SDK v2），v3.x 有不兼容的 API 变更。
- **AI 模型**：`glm-4-flash`（智谱 AI）— 速度快、免费额度充足、中文支持优秀。
- **查询过滤**：仅查询 `领域=🏢工作` 的笔记，按 `Date` 属性筛选日期范围。
- **周报作者**：通过 `WEEKLY_REPORT_AUTHOR` 环境变量配置，默认为 `shanks`。
