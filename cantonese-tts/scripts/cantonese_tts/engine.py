"""粤语转换引擎：协调翻译器和 TTS 引擎完成完整工作流"""

import os
import time
from pathlib import Path
from typing import Optional, Dict

from .base import TranslationResult, TTSResult, ConversionResult
from .config import load_config, validate_config
from .registry import (
    get_translator, get_tts_engine,
    list_translators, list_tts_engines,
)

# 确保插件被加载
from . import translators
from . import tts_engines


class CantoneseEngine:
    """粤语转换引擎"""

    def __init__(self, config: Optional[Dict] = None, config_path: Optional[str] = None):
        if config is None:
            config = load_config(config_path)
        self.config = config
        self._translator = None
        self._tts_engine = None

    @property
    def translator(self):
        if self._translator is None:
            t_config = self.config["translator"]
            t_type = t_config.pop("type", "zhipu")
            self._translator = get_translator(t_type, **t_config)
            t_config["type"] = t_type
        return self._translator

    @property
    def tts_engine(self):
        if self._tts_engine is None:
            tts_config = self.config["tts"]
            tts_type = tts_config.pop("type", "edge")
            self._tts_engine = get_tts_engine(tts_type, **tts_config)
            tts_config["type"] = tts_type
        return self._tts_engine

    def translate(self, text: str) -> TranslationResult:
        """仅翻译普通话为粤语"""
        print(f"🔄 翻译中 [{self.config['translator'].get('type', 'zhipu')}]...")
        result = self.translator.translate(text)
        print(f"✅ 翻译完成: {result.cantonese_text}")
        return result

    def synthesize(self, cantonese_text: str, output_path: Optional[str] = None) -> TTSResult:
        """将粤语文本合成为语音"""
        if output_path is None:
            output_dir = self.config.get("output", {}).get("dir", "./output")
            fmt = self.config.get("output", {}).get("format", "mp3")
            timestamp = int(time.time())
            output_path = os.path.join(output_dir, f"cantonese_{timestamp}.{fmt}")

        print(f"🔊 合成语音中 [{self.config['tts'].get('type', 'edge')}]...")
        result = self.tts_engine.synthesize(cantonese_text, Path(output_path))
        print(f"✅ 语音已保存: {result.audio_path}")
        return result

    def convert(self, text: str, output_path: Optional[str] = None) -> ConversionResult:
        """完整工作流：翻译 + 语音合成"""
        translation = self.translate(text)
        tts = self.synthesize(translation.cantonese_text, output_path)
        return ConversionResult(translation=translation, tts=tts)

    def validate(self) -> list:
        """验证配置"""
        errors = validate_config(self.config)

        # 验证翻译器
        try:
            if not self.translator.validate():
                errors.append(f"翻译器 {self.config['translator'].get('type')} 验证失败")
        except Exception as e:
            errors.append(f"翻译器初始化失败: {e}")

        # 验证 TTS 引擎
        try:
            if not self.tts_engine.validate():
                errors.append(f"TTS 引擎 {self.config['tts'].get('type')} 验证失败")
        except Exception as e:
            errors.append(f"TTS 引擎初始化失败: {e}")

        return errors

    def list_plugins(self):
        """列出所有可用插件"""
        print("\n📋 可用翻译器:")
        for name in list_translators():
            marker = " ← 当前" if name == self.config["translator"].get("type") else ""
            print(f"  - {name}{marker}")

        print("\n📋 可用 TTS 引擎:")
        for name in list_tts_engines():
            marker = " ← 当前" if name == self.config["tts"].get("type") else ""
            print(f"  - {name}{marker}")

        # 列出 TTS 引擎的粤语音色
        try:
            voices = self.tts_engine.list_voices()
            if voices:
                print(f"\n🎤 当前 TTS 引擎 ({self.config['tts'].get('type')}) 粤语音色:")
                for v in voices:
                    print(f"  - {v['id']}: {v['name']} ({v.get('gender', 'Unknown')})")
        except Exception:
            pass
