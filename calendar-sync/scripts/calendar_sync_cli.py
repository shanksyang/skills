#!/usr/bin/env python3
"""
通用日历同步工具 - CLI 入口

支持多种日历源（CalDAV/Google/Outlook/iCal）、
多种 AI 模型（智谱/OpenAI/Claude/Ollama）和
多种笔记应用（Notion/Obsidian/Logseq/Markdown）。

使用方式:
    python3 calendar_sync_cli.py                             # 同步（使用配置文件）
    python3 calendar_sync_cli.py --test                      # 测试模式
    python3 calendar_sync_cli.py --list-calendars            # 列出日历
    python3 calendar_sync_cli.py --config my_config.yaml     # 指定配置
    python3 calendar_sync_cli.py --days-back 14              # 自定义时间范围
    python3 calendar_sync_cli.py --calendar "shanksyang"     # 指定日历
    python3 calendar_sync_cli.py --list-plugins              # 列出可用插件
"""

import argparse
import sys
from pathlib import Path

# 确保包可导入
sys.path.insert(0, str(Path(__file__).parent))

# 导入插件（触发注册）
from calendar_sync import sources  # noqa: F401
from calendar_sync import classifiers  # noqa: F401
from calendar_sync import writers  # noqa: F401

from calendar_sync.config import load_config
from calendar_sync.engine import SyncEngine
from calendar_sync.registry import PluginRegistry


def list_plugins():
    """列出所有可用插件"""
    print("=" * 60)
    print("可用插件")
    print("=" * 60)

    print("\n📅 日历源 (source.type):")
    for name in PluginRegistry.list_sources():
        print(f"  - {name}")

    print("\n🤖 AI 分类器 (ai.type):")
    for name in PluginRegistry.list_classifiers():
        print(f"  - {name}")

    print("\n📝 笔记输出 (output.type):")
    for name in PluginRegistry.list_writers():
        print(f"  - {name}")

    print(f"\n{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="通用日历同步工具 - 支持多种日历源、AI 模型和笔记应用"
    )
    parser.add_argument("--config", type=str, default=None, help="配置文件路径 (YAML)")
    parser.add_argument("--days-back", type=int, default=7, help="向前同步天数（默认7）")
    parser.add_argument("--days-forward", type=int, default=30, help="向后同步天数（默认30）")
    parser.add_argument("--calendar", type=str, default=None, help="仅同步指定名称的日历")
    parser.add_argument("--list-calendars", action="store_true", help="列出所有日历")
    parser.add_argument("--list-plugins", action="store_true", help="列出所有可用插件")
    parser.add_argument("--test", action="store_true", help="测试模式（不写入笔记）")
    parser.add_argument("--validate", action="store_true", help="验证配置")
    args = parser.parse_args()

    if args.list_plugins:
        list_plugins()
        return

    # 加载配置
    config = load_config(args.config)

    # 创建同步引擎
    engine = SyncEngine(config)

    if args.validate:
        engine.validate()
    elif args.list_calendars:
        engine.list_calendars()
    elif args.test:
        engine.test(args.days_back, args.days_forward, args.calendar)
    else:
        if not engine.validate():
            print("\n⚠ 配置验证失败，请修正后重试")
            sys.exit(1)
        engine.sync(args.days_back, args.days_forward, args.calendar)


if __name__ == "__main__":
    main()
