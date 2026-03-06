# Notion 文件 API 说明

## 文件 Block 类型

Notion 支持两种文件 block：

### 1. External File（外部链接）

通过外部 URL 引用文件，无大小限制：

```python
{
    "object": "block",
    "type": "file",
    "file": {
        "type": "external",
        "external": {
            "url": "https://example.com/file.pdf"
        }
    }
}
```

**适用场景**：大文件、已存在于云存储的文件

### 2. Notion 托管文件（API 上传）

通过 Notion API 上传文件，**上限 5MB**：

使用流程：
1. 调用 `files.upload` 获取上传 URL（需要 Notion API 2025-02+ 版本）
2. 上传文件到该 URL
3. 在页面 block 中引用文件 ID

> **注意**：截至 2025 年，Notion 公开 API 的文件上传能力仍在逐步开放中。
> 推荐方案：对于需要上传的文件，使用 External File block + 外部存储链接。

## 在页面创建时添加文件

```python
from notion_client import Client

client = Client(auth=token)

# 创建页面时附带文件 block
client.pages.create(
    parent={"database_id": database_id},
    properties={
        "title": {"title": [{"text": {"content": "文件标题"}}]},
        "标签": {"multi_select": [{"name": "附件"}]},
    },
    children=[
        # 文件描述
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "文件说明..."}}]
            }
        },
        # 外部文件链接
        {
            "object": "block",
            "type": "file",
            "file": {
                "type": "external",
                "external": {"url": "https://example.com/file.pdf"}
            }
        },
        # 或者嵌入链接（bookmark）
        {
            "object": "block",
            "type": "bookmark",
            "bookmark": {
                "url": "https://example.com/file.pdf"
            }
        },
    ]
)
```

## 向已有页面追加文件 Block

```python
# 获取页面 ID 后追加 block
client.blocks.children.append(
    block_id=page_id,
    children=[
        {
            "object": "block",
            "type": "file",
            "file": {
                "type": "external",
                "external": {"url": "https://example.com/new-file.pdf"}
            }
        }
    ]
)
```

## 图片 Block（特殊文件类型）

图片可以使用专用的 `image` block：

```python
{
    "object": "block",
    "type": "image",
    "image": {
        "type": "external",
        "external": {"url": "https://example.com/photo.png"}
    }
}
```

支持格式：PNG、JPG、GIF、SVG、WebP、BMP、ICO、TIFF

## Embed Block（嵌入链接）

对于支持嵌入的链接（如 Google Drive、Dropbox 公开链接）：

```python
{
    "object": "block",
    "type": "embed",
    "embed": {
        "url": "https://drive.google.com/file/d/xxx/view"
    }
}
```

## API 限制总结

| 限制项 | 值 |
|--------|-----|
| API 上传文件大小 | 5MB |
| External URL 文件 | 无大小限制 |
| 每次 API 调用最大 block 数 | 100 |
| API 速率限制 | 3 请求/秒 |
| Rich text 最大长度 | 2000 字符 |
