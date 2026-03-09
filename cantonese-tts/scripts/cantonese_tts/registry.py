"""插件注册表：管理翻译器和 TTS 引擎的注册与获取"""

from typing import Dict, Type
from .base import Translator, TTSEngine

_translators: Dict[str, Type[Translator]] = {}
_tts_engines: Dict[str, Type[TTSEngine]] = {}


def register_translator(name: str):
    """注册翻译器插件"""
    def decorator(cls):
        _translators[name] = cls
        cls.name = name
        return cls
    return decorator


def register_tts_engine(name: str):
    """注册 TTS 引擎插件"""
    def decorator(cls):
        _tts_engines[name] = cls
        cls.name = name
        return cls
    return decorator


def get_translator(name: str, **kwargs) -> Translator:
    """获取翻译器实例"""
    if name not in _translators:
        available = ", ".join(_translators.keys())
        raise ValueError(f"未知的翻译器: {name}。可用翻译器: {available}")
    return _translators[name](**kwargs)


def get_tts_engine(name: str, **kwargs) -> TTSEngine:
    """获取 TTS 引擎实例"""
    if name not in _tts_engines:
        available = ", ".join(_tts_engines.keys())
        raise ValueError(f"未知的 TTS 引擎: {name}。可用引擎: {available}")
    return _tts_engines[name](**kwargs)


def list_translators() -> list:
    """列出所有可用翻译器"""
    return list(_translators.keys())


def list_tts_engines() -> list:
    """列出所有可用 TTS 引擎"""
    return list(_tts_engines.keys())
