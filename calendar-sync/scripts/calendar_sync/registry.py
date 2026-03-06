"""
插件注册表 - 管理所有可用插件
"""

from typing import Optional


class PluginRegistry:
    """全局插件注册表"""

    _sources: dict = {}
    _classifiers: dict = {}
    _writers: dict = {}

    @classmethod
    def register_source(cls, name: str, plugin_cls):
        cls._sources[name] = plugin_cls

    @classmethod
    def register_classifier(cls, name: str, plugin_cls):
        cls._classifiers[name] = plugin_cls

    @classmethod
    def register_writer(cls, name: str, plugin_cls):
        cls._writers[name] = plugin_cls

    @classmethod
    def get_source(cls, name: str) -> Optional[type]:
        return cls._sources.get(name)

    @classmethod
    def get_classifier(cls, name: str) -> Optional[type]:
        return cls._classifiers.get(name)

    @classmethod
    def get_writer(cls, name: str) -> Optional[type]:
        return cls._writers.get(name)

    @classmethod
    def list_sources(cls) -> list[str]:
        return list(cls._sources.keys())

    @classmethod
    def list_classifiers(cls) -> list[str]:
        return list(cls._classifiers.keys())

    @classmethod
    def list_writers(cls) -> list[str]:
        return list(cls._writers.keys())
