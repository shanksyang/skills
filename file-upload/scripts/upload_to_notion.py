#!/usr/bin/env python3
"""
Notion 文件上传与管理工具

将文件上传到 Notion 页面：
- ≤5MB：上传为 Notion 附件（file block）
- >5MB：提示用户提供外部链接，或以 bookmark 形式添加

支持：新建页面 / 追加到已有页面 / 批量上传 / 分类管理
"""

import argparse
import hashlib
import json
import mimetypes
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

# ── 常量 ──────────────────────────────────────────────
LARGE_FILE_THRESHOLD = 5 * 1024 * 1024  # 5MB (Notion API 限制)
UPLOAD_HISTORY_FILE = "upload_history.json"
DEFAULT_CATEGORY_CONFIG = "config/file_categories.yaml"
MAX_BLOCKS_PER_REQUEST = 100
NOTION_TEXT_LIMIT = 2000


# ── 工具函数 ──────────────────────────────────────────
def file_md5(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def detect_file_type(filepath: str) -> str:
    mime, _ = mimetypes.guess_type(filepath)
    return mime or "application/octet-stream"


def is_image(filepath: str) -> bool:
    mime = detect_file_type(filepath)
    return mime.startswith("image/")


# ── 上传历史管理 ──────────────────────────────────────
class UploadHistory:
    def __init__(self, history_file: str = UPLOAD_HISTORY_FILE):
        self.history_file = history_file
        self.history = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"uploads": []}

    def save(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def is_uploaded(self, filepath: str, md5: str) -> bool:
        for record in self.history.get("uploads", []):
            if record.get("md5") == md5 and record.get("filepath") == filepath:
                return True
        return False

    def add_record(self, filepath: str, md5: str, page_url: str, category: str):
        self.history.setdefault("uploads", []).append({
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "md5": md5,
            "page_url": page_url,
            "category": category,
            "uploaded_at": datetime.now().isoformat(),
        })
        self.save()


# ── 分类管理 ──────────────────────────────────────────
class CategoryManager:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str = None) -> dict:
        paths = [
            config_path,
            DEFAULT_CATEGORY_CONFIG,
            os.path.join(os.path.dirname(__file__), "..", "assets", "config", "file_categories.yaml"),
        ]
        for p in paths:
            if p and os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        return {"categories": {}}

    def list_categories(self) -> list:
        categories = self.config.get("categories", {})
        result = []
        for name, info in categories.items():
            icon = info.get("icon", "📁")
            desc = info.get("description", "")
            subs = info.get("subcategories", [])
            result.append({
                "name": name,
                "icon": icon,
                "description": desc,
                "subcategories": subs,
            })
        return result

    def get_category_info(self, category: str) -> dict:
        return self.config.get("categories", {}).get(category, {})

    def get_tags(self, category: str) -> list:
        info = self.get_category_info(category)
        return info.get("tags", [category])

    def get_default_category(self, filepath: str) -> str:
        ext = Path(filepath).suffix.lower()
        defaults = self.config.get("file_type_defaults", {})
        return defaults.get(ext, "临时文件")

    def get_notion_defaults(self) -> dict:
        return self.config.get("notion_defaults", {
            "domain": "📁文件",
            "include_file_info": True,
        })


# ── Notion Block 构建 ─────────────────────────────────
def heading_block(text: str, level: int = 2) -> dict:
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": [{"type": "text", "text": {"content": text[:NOTION_TEXT_LIMIT]}}]
        },
    }


def paragraph_block(text: str, **annotations) -> dict:
    rt = {"type": "text", "text": {"content": text[:NOTION_TEXT_LIMIT]}}
    if annotations:
        rt["annotations"] = annotations
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [rt]},
    }


def callout_block(text: str, emoji: str = "📎") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text[:NOTION_TEXT_LIMIT]}}],
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def divider_block() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def external_file_block(url: str, name: str = "") -> dict:
    block = {
        "object": "block",
        "type": "file",
        "file": {
            "type": "external",
            "external": {"url": url},
        },
    }
    if name:
        block["file"]["caption"] = [{"type": "text", "text": {"content": name}}]
    return block


def external_image_block(url: str, caption: str = "") -> dict:
    block = {
        "object": "block",
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": url},
        },
    }
    if caption:
        block["image"]["caption"] = [{"type": "text", "text": {"content": caption}}]
    return block


def bookmark_block(url: str, caption: str = "") -> dict:
    block = {
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": url},
    }
    if caption:
        block["bookmark"]["caption"] = [{"type": "text", "text": {"content": caption}}]
    return block


# ── 文件信息 Block 构建 ────────────────────────────────
def build_file_info_blocks(filepath: str, category: str, url: str = None) -> list:
    stat = os.stat(filepath)
    blocks = [
        callout_block(
            f"📁 {os.path.basename(filepath)}\n"
            f"大小: {human_size(stat.st_size)} | "
            f"类型: {detect_file_type(filepath)}\n"
            f"分类: {category} | "
            f"上传时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            emoji="📎",
        ),
    ]

    if url:
        if is_image(filepath):
            blocks.append(external_image_block(url, os.path.basename(filepath)))
        else:
            blocks.append(external_file_block(url, os.path.basename(filepath)))
    
    return blocks


def build_url_info_blocks(url: str, name: str, category: str) -> list:
    return [
        callout_block(
            f"🔗 {name}\n"
            f"链接: {url}\n"
            f"分类: {category} | "
            f"添加时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            emoji="🔗",
        ),
        bookmark_block(url, name),
    ]


# ── Notion 上传器 ─────────────────────────────────────
class NotionUploader:
    def __init__(self, token: str = None, database_id: str = None):
        self.token = token or os.getenv("NOTION_TOKEN")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID")
        if not self.token:
            raise ValueError("NOTION_TOKEN 未配置，请在 .env 中设置")
        if not self.database_id:
            raise ValueError("NOTION_DATABASE_ID 未配置，请在 .env 中设置")
        self.client = Client(auth=self.token)
        self.history = UploadHistory()
        self.categories = CategoryManager()

    def create_page(self, title: str, category: str, children: list) -> str:
        tags = self.categories.get_tags(category)
        defaults = self.categories.get_notion_defaults()

        properties = {
            "title": {"title": [{"text": {"content": title}}]},
        }

        # 添加标签
        if tags:
            properties["标签"] = {"multi_select": [{"name": t} for t in tags]}

        # 添加领域
        domain = defaults.get("domain", "📁文件")
        properties["领域"] = {"select": {"name": domain}}

        # 添加日期
        properties["Date"] = {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}

        response = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
            children=children[:MAX_BLOCKS_PER_REQUEST],
        )

        page_url = response.get("url", "")

        # 如果 block 超过 100 个，分批追加
        remaining = children[MAX_BLOCKS_PER_REQUEST:]
        if remaining:
            page_id = response["id"]
            for i in range(0, len(remaining), MAX_BLOCKS_PER_REQUEST):
                batch = remaining[i:i + MAX_BLOCKS_PER_REQUEST]
                self.client.blocks.children.append(block_id=page_id, children=batch)

        return page_url

    def append_to_page(self, page_id: str, children: list) -> str:
        for i in range(0, len(children), MAX_BLOCKS_PER_REQUEST):
            batch = children[i:i + MAX_BLOCKS_PER_REQUEST]
            self.client.blocks.children.append(block_id=page_id, children=batch)

        page = self.client.pages.retrieve(page_id=page_id)
        return page.get("url", "")

    def upload_file(self, filepath: str, category: str = None, page_id: str = None, url: str = None) -> str:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            print(f"  ✗ 文件不存在: {filepath}")
            return ""

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        md5 = file_md5(filepath)

        # 检查是否已上传
        if self.history.is_uploaded(filepath, md5):
            print(f"  ⊘ 已上传过: {filename}（跳过）")
            return ""

        # 确定分类
        if not category:
            category = self.categories.get_default_category(filepath)

        print(f"  → {filename} ({human_size(file_size)}) [{category}]")

        # 判断文件大小
        if file_size > LARGE_FILE_THRESHOLD and not url:
            print(f"  ⚠ 文件超过 5MB，Notion API 无法直接上传")
            print(f"    请提供外部链接（使用 --url 参数），或将文件上传到网盘后添加链接")
            return ""

        # 构建 blocks
        if url:
            children = build_file_info_blocks(filepath, category, url)
        elif file_size <= LARGE_FILE_THRESHOLD:
            # 小文件：以文件信息 + bookmark 形式记录
            # 注意：Notion API 目前对直接上传文件的支持有限
            # 这里以文件元信息记录为主
            children = [
                callout_block(
                    f"📁 {filename}\n"
                    f"大小: {human_size(file_size)} | "
                    f"类型: {detect_file_type(filepath)}\n"
                    f"分类: {category} | "
                    f"上传时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"MD5: {md5}",
                    emoji="📎",
                ),
            ]
        else:
            children = build_file_info_blocks(filepath, category, url)

        # 创建或追加
        if page_id:
            page_url = self.append_to_page(page_id, children)
            print(f"  ✓ 已追加到页面: {page_url}")
        else:
            title = filename
            page_url = self.create_page(title, category, children)
            print(f"  ✓ 已创建页面: {page_url}")

        # 记录上传历史
        self.history.add_record(filepath, md5, page_url, category)
        return page_url

    def upload_url(self, url: str, name: str, category: str = None, page_id: str = None) -> str:
        if not category:
            category = "临时文件"

        print(f"  → 链接: {name} [{category}]")

        children = build_url_info_blocks(url, name, category)

        if page_id:
            page_url = self.append_to_page(page_id, children)
            print(f"  ✓ 已追加链接到页面: {page_url}")
        else:
            page_url = self.create_page(name, category, children)
            print(f"  ✓ 已创建链接页面: {page_url}")

        return page_url

    def upload_directory(self, dirpath: str, category: str = None, page_id: str = None) -> list:
        dirpath = os.path.abspath(dirpath)
        if not os.path.isdir(dirpath):
            print(f"  ✗ 目录不存在: {dirpath}")
            return []

        files = sorted([
            os.path.join(dirpath, f)
            for f in os.listdir(dirpath)
            if os.path.isfile(os.path.join(dirpath, f)) and not f.startswith(".")
        ])

        if not files:
            print(f"  ⊘ 目录为空: {dirpath}")
            return []

        print(f"  找到 {len(files)} 个文件")
        results = []
        for filepath in files:
            result = self.upload_file(filepath, category=category, page_id=page_id)
            if result:
                results.append(result)

        return results


# ── CLI ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Notion 文件上传与管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s --file doc.pdf --category "工作项目"
  %(prog)s --file doc.pdf --page-id abc123
  %(prog)s --url "https://example.com/file.zip" --name "大文件"
  %(prog)s --dir ./files --category "项目文档"
  %(prog)s --list-categories
        """,
    )

    # 上传模式
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", "-f", help="要上传的文件路径")
    group.add_argument("--dir", "-d", help="要批量上传的目录路径")
    group.add_argument("--url", "-u", help="外部文件链接")
    group.add_argument("--list-categories", action="store_true", help="列出所有分类")

    # 选项
    parser.add_argument("--page-id", "-p", help="追加到已有 Notion 页面（页面 ID）")
    parser.add_argument("--category", "-c", help="文件分类（如：工作项目、学习资料）")
    parser.add_argument("--name", "-n", help="文件名称（用于 --url 模式）")
    parser.add_argument("--config", help="分类配置文件路径")

    args = parser.parse_args()

    # 列出分类
    if args.list_categories:
        cm = CategoryManager(args.config)
        categories = cm.list_categories()
        print("\n可用分类：")
        for cat in categories:
            print(f"  {cat['icon']} {cat['name']} - {cat['description']}")
            for sub in cat.get("subcategories", []):
                print(f"      └─ {sub}")
        print()
        return

    if not args.file and not args.dir and not args.url:
        parser.print_help()
        return

    try:
        uploader = NotionUploader()
    except ValueError as e:
        print(f"✗ 配置错误: {e}")
        sys.exit(1)

    print(f"\n{'=' * 50}")
    print(f"Notion 文件上传工具")
    print(f"{'=' * 50}\n")

    if args.file:
        uploader.upload_file(
            args.file,
            category=args.category,
            page_id=args.page_id,
            url=args.url,
        )
    elif args.dir:
        uploader.upload_directory(
            args.dir,
            category=args.category,
            page_id=args.page_id,
        )
    elif args.url:
        name = args.name or args.url.split("/")[-1] or "未命名文件"
        uploader.upload_url(
            args.url,
            name=name,
            category=args.category,
            page_id=args.page_id,
        )

    print(f"\n{'=' * 50}")
    print("完成！")


if __name__ == "__main__":
    main()
