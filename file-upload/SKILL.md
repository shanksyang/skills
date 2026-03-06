---
name: file-upload
description: "Notion 文件上传与管理工具。This skill should be used when users need to upload files to Notion pages, manage file attachments in Notion, organize files by project/category, or add file links to existing Notion notes. Covers file upload, category management, and Notion page creation with attachments."
---

# Notion 文件上传与管理工具

将文件上传到 Notion 页面（小文件作为附件，大文件存链接），支持按项目/用途分类管理。

## 概述

核心工作流：本地文件 → 分类判断 → Notion 页面（附件/链接）

```
本地文件
   ↓
upload_to_notion.py（上传引擎）
   ↓
文件大小判断（≤5MB 附件 / >5MB 链接）
   ↓
Notion 页面（新建 / 追加到已有页面）
```

### Notion 文件限制

| 限制项 | 值 |
|--------|-----|
| 单个附件上限（API 上传） | **5MB**（Notion API 限制） |
| External URL 文件引用 | 无大小限制 |
| 页面 block 数上限 | 无硬限制 |

> **注意**：Notion API 上传文件限制为 5MB，不是 100MB。超过 5MB 的文件需要先上传到外部存储，然后以链接形式添加到 Notion。

## 使用场景

- 用户需要上传文件到 Notion 笔记
- 用户提到"上传文件"、"添加附件"、"文件管理"、"文件分类"
- 用户希望将文件链接同步到 Notion
- 用户需要按项目分类管理文件
- 用户需要在已有 Notion 笔记中添加文件

## 脚本

### `scripts/upload_to_notion.py`

文件上传主脚本，可直接执行。

**命令：**
```bash
# 上传文件到新建 Notion 页面（自动判断附件/链接）
python3 scripts/upload_to_notion.py --file /path/to/doc.pdf --category "工作项目A"

# 上传文件并追加到已有 Notion 页面
python3 scripts/upload_to_notion.py --file /path/to/doc.pdf --page-id <notion_page_id>

# 添加外部链接到 Notion 页面
python3 scripts/upload_to_notion.py --url "https://example.com/large-file.zip" --name "大文件" --category "项目资料"

# 批量上传目录下所有文件
python3 scripts/upload_to_notion.py --dir /path/to/folder --category "项目文档"

# 指定分类配置文件
python3 scripts/upload_to_notion.py --file /path/to/doc.pdf --config file_categories.yaml

# 列出所有分类
python3 scripts/upload_to_notion.py --list-categories
```

**核心特性：**
- 自动检测文件大小：≤5MB 作为 Notion 附件上传，>5MB 提示用户提供外部链接
- 支持新建 Notion 页面或追加到已有页面
- 按项目/用途自定义分类（通过 YAML 配置）
- 批量上传目录下所有文件
- 支持直接添加外部 URL 链接
- 上传记录保存到 `upload_history.json`，避免重复上传

**支持的文件类型：**
- 文档：PDF、Word、Excel、PPT、TXT、Markdown
- 图片：PNG、JPG、GIF、SVG、WebP
- 压缩包：ZIP、RAR、7z、TAR.GZ
- 其他：任意文件类型均可上传

### `scripts/setup_file_upload.sh`

项目初始化脚本：
```bash
bash scripts/setup_file_upload.sh /path/to/project
```

创建：上传脚本、配置目录、`.env.example`、`requirements.txt`。

## 参考文档

### `references/environment_setup.md`

帮助用户配置环境变量、安装依赖或排查问题时阅读。包含：
- Notion Token 和 Database ID 的获取方式
- Python 依赖版本说明
- 环境变量配置
- 验证命令

### `references/notion_file_api.md`

理解 Notion 文件 API 能力或调试上传问题时阅读。包含：
- Notion API 文件上传限制（5MB）
- File block 和 External file block 的区别
- 页面创建时添加文件的方法
- 向已有页面追加 block 的方法

## 资源文件

### `assets/config/file_categories.yaml`

文件分类配置模板，定义项目/用途分类结构。复制到项目的 `config/` 目录使用。

## 工作流：上传文件到新 Notion 页面

1. 确保 `.env` 中配置了 `NOTION_TOKEN` 和 `NOTION_DATABASE_ID`
2. 准备要上传的文件
3. 运行 `python3 upload_to_notion.py --file /path/to/file --category "分类名"`
4. 脚本自动判断文件大小：
   - ≤5MB → 上传为 Notion 附件（file block）
   - >5MB → 提示用户提供外部链接，或自动跳过
5. 创建 Notion 页面，包含文件信息、分类标签

## 工作流：添加文件到已有 Notion 页面

1. 获取目标 Notion 页面的 page_id
2. 运行 `python3 upload_to_notion.py --file /path/to/file --page-id <page_id>`
3. 文件以 block 形式追加到页面末尾

## 工作流：批量上传

1. 将文件整理到一个目录中
2. 运行 `python3 upload_to_notion.py --dir /path/to/folder --category "项目名"`
3. 每个文件创建独立的 Notion 页面，或全部追加到同一页面（使用 `--page-id`）

## 工作流：问题排查

| 问题 | 解决方案 |
|------|----------|
| 上传失败 "file too large" | Notion API 限制 5MB，改用外部链接方式 |
| Notion API 报错 401 | 检查 `NOTION_TOKEN` 是否正确，Integration 是否已关联到目标数据库 |
| 页面创建成功但看不到文件 | 确认 Integration 有写入权限，检查 block 类型是否正确 |
| 批量上传中断 | 脚本支持断点续传，已上传的文件记录在 `upload_history.json` 中 |
| 分类不存在 | 运行 `--list-categories` 查看可用分类，或编辑 `file_categories.yaml` 新增 |

## 关键技术细节

- **Notion API 版本**：必须使用 `notion-client==2.2.1`（v3 有不兼容变更）
- **文件上传限制**：Notion API 单文件上传上限 5MB，超过需用 external URL
- **File Block 类型**：`file`（Notion 托管）和 `external`（外部 URL）两种
- **页面追加**：使用 `blocks.children.append` API 向已有页面添加 block
- **上传去重**：基于文件路径 + MD5 哈希记录上传历史，避免重复
