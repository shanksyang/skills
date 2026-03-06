"""
同步引擎 - 核心协调逻辑
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .base import CalendarSource, AIClassifier, NoteWriter, CalendarEvent, Classification
from .registry import PluginRegistry


class SyncEngine:
    """通用日历同步引擎"""

    def __init__(self, config: dict, state_file: Optional[Path] = None):
        self.config = config
        self.state_file = state_file or Path("sync_state.json")

        # 从配置初始化插件
        self.source: CalendarSource = self._init_source()
        self.classifier: AIClassifier = self._init_classifier()
        self.writer: NoteWriter = self._init_writer()

    def _init_source(self) -> CalendarSource:
        source_cfg = self.config.get("source", {})
        source_type = source_cfg.get("type", "caldav")
        cls = PluginRegistry.get_source(source_type)
        if not cls:
            raise ValueError(f"未知的日历源类型: {source_type}，可用: {PluginRegistry.list_sources()}")
        return cls(source_cfg)

    def _init_classifier(self) -> AIClassifier:
        ai_cfg = self.config.get("ai", {})
        ai_type = ai_cfg.get("type", "keyword")
        cls = PluginRegistry.get_classifier(ai_type)
        if not cls:
            raise ValueError(f"未知的 AI 分类器类型: {ai_type}，可用: {PluginRegistry.list_classifiers()}")
        return cls(ai_cfg)

    def _init_writer(self) -> NoteWriter:
        output_cfg = self.config.get("output", {})
        output_type = output_cfg.get("type", "notion")
        cls = PluginRegistry.get_writer(output_type)
        if not cls:
            raise ValueError(f"未知的笔记输出类型: {output_type}，可用: {PluginRegistry.list_writers()}")
        return cls(output_cfg)

    def validate(self) -> bool:
        """验证所有插件配置"""
        all_ok = True
        for name, plugin in [("日历源", self.source), ("AI分类", self.classifier), ("笔记输出", self.writer)]:
            missing = plugin.validate_config()
            if missing:
                print(f"✗ {name} ({plugin.name}) 缺少配置: {', '.join(missing)}")
                all_ok = False
            else:
                print(f"✓ {name}: {plugin.name}")
        return all_ok

    def list_calendars(self):
        """列出所有可用日历"""
        print(f"正在连接 {self.source.name}...")
        self.source.connect()
        calendars = self.source.list_calendars()
        print(f"✓ 找到 {len(calendars)} 个日历")
        for cal in calendars:
            print(f"  - {cal['name']} (id: {cal['id']})")
        return calendars

    def test(self, days_back=7, days_forward=30, calendar_name=None):
        """测试模式：读取 + 分类，不写入"""
        print("=" * 60)
        print(f"日历同步测试 [{self.source.name}] → [{self.classifier.name}]")
        print("=" * 60)

        self.source.connect()
        calendars = self.source.list_calendars()
        if calendar_name:
            calendars = [c for c in calendars if calendar_name in c["name"]]
            if not calendars:
                print(f"⚠ 没有找到名称包含 '{calendar_name}' 的日历")
                return

        now = datetime.now()
        start = now - timedelta(days=days_back)
        end = now + timedelta(days=days_forward)
        print(f"时间范围: {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}")

        total = 0
        for cal in calendars:
            print(f"\n--- 日历: {cal['name']} ---")
            events = self.source.fetch_events(cal["id"], start, end)

            for event in events:
                total += 1
                classification = self.classifier.classify(event)
                start_str = event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else "?"
                end_str = event.end_time.strftime("%H:%M") if event.end_time else "?"
                print(f"\n  [{total}] {event.summary}")
                print(f"      时间: {start_str} ~ {end_str}")
                print(f"      分类: {classification.category}")
                print(f"      标签: {classification.tags}")
                print(f"      模板: {classification.event_type}")
                if event.location:
                    print(f"      地点: {event.location}")

        print(f"\n{'=' * 60}")
        print(f"测试完成! 共读取并分类 {total} 个日程事件")
        print(f"{'=' * 60}")

    def sync(self, days_back=7, days_forward=30, calendar_name=None):
        """完整同步"""
        print("=" * 60)
        print(f"日历同步 [{self.source.name}] → [{self.classifier.name}] → [{self.writer.name}]")
        print("=" * 60)

        self.source.connect()
        calendars = self.source.list_calendars()
        if not calendars:
            print("⚠ 没有找到任何日历")
            return

        if calendar_name:
            calendars = [c for c in calendars if calendar_name in c["name"]]
            if not calendars:
                print(f"⚠ 没有找到名称包含 '{calendar_name}' 的日历")
                return
            print(f"✓ 已筛选日历: {[c['name'] for c in calendars]}")

        synced_uids = self._load_synced_uids()
        print(f"已同步事件数: {len(synced_uids)}")

        now = datetime.now()
        start = now - timedelta(days=days_back)
        end = now + timedelta(days=days_forward)
        print(f"时间范围: {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}")

        new_count = 0
        skip_count = 0
        dup_count = 0
        fail_count = 0

        for cal in calendars:
            print(f"\n--- 日历: {cal['name']} ---")
            events = self.source.fetch_events(cal["id"], start, end)

            for event in events:
                if event.uid in synced_uids:
                    skip_count += 1
                    continue

                try:
                    classification = self.classifier.classify(event)
                    url = self.writer.write(event, classification)

                    # 检查是否是服务端检测到的重复
                    if isinstance(url, str) and url.startswith("SKIP_DUP:"):
                        synced_uids.add(event.uid)
                        dup_count += 1
                        print(f"  ⊘ {event.summary} (Notion已存在，补录UID)")
                    else:
                        synced_uids.add(event.uid)
                        new_count += 1
                        print(f"  ✓ {event.summary}")
                        print(f"    分类={classification.category} 标签={classification.tags}")
                        if url:
                            print(f"    → {url}")
                except Exception as e:
                    print(f"  ✗ 创建失败 ({event.summary}): {e}")
                    fail_count += 1

        self._save_synced_uids(synced_uids)

        print(f"\n{'=' * 60}")
        print(f"同步完成!")
        print(f"  新增: {new_count}")
        print(f"  跳过(已同步): {skip_count}")
        if dup_count:
            print(f"  服务端去重: {dup_count}")
        if fail_count:
            print(f"  失败: {fail_count}")
        print(f"  累计已同步: {len(synced_uids)}")
        print(f"{'=' * 60}")

    def _load_synced_uids(self) -> set:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return set(data.get("synced_uids", []))
            except (json.JSONDecodeError, KeyError):
                return set()
        return set()

    def _save_synced_uids(self, uids: set):
        data = {
            "synced_uids": sorted(uids),
            "last_sync": datetime.now().isoformat(),
            "total_synced": len(uids),
        }
        self.state_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
