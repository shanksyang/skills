"""配置管理：支持 YAML 配置文件和环境变量"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def _resolve_env_vars(value: str) -> str:
    """解析 ${ENV_VAR} 格式的环境变量引用"""
    def replace_env(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name, "")
        if not env_value:
            print(f"  ⚠ 环境变量 {var_name} 未设置")
        return env_value
    return re.sub(r'\$\{(\w+)\}', replace_env, value)


def _resolve_config_values(config: Any) -> Any:
    """递归解析配置中的环境变量"""
    if isinstance(config, str):
        return _resolve_env_vars(config)
    elif isinstance(config, dict):
        return {k: _resolve_config_values(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_resolve_config_values(item) for item in config]
    return config


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    加载配置文件
    
    优先级：
    1. 指定的 config_path
    2. cantonese_tts.yaml
    3. config/cantonese_tts.yaml
    4. 仅使用环境变量
    """
    # 尝试加载 .env 文件
    try:
        from dotenv import load_dotenv
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            print(f"  ✓ 已加载 .env 文件")
    except ImportError:
        pass

    # 查找配置文件
    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.extend([
        Path("cantonese_tts.yaml"),
        Path("config/cantonese_tts.yaml"),
    ])

    config = {}
    for path in search_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            print(f"  ✓ 已加载配置文件: {path}")
            break

    # 解析环境变量
    config = _resolve_config_values(config)

    # 设置默认值
    config.setdefault("translator", {})
    config.setdefault("tts", {})
    config.setdefault("output", {"dir": "./output", "format": "mp3"})

    # 翻译器默认配置
    translator = config["translator"]
    translator.setdefault("type", "zhipu")

    # TTS 默认配置
    tts = config["tts"]
    tts.setdefault("type", "edge")

    # 从环境变量补充缺失配置
    _fill_from_env(config)

    return config


def _fill_from_env(config: Dict):
    """从环境变量补充缺失的配置项"""
    translator = config["translator"]
    tts = config["tts"]

    # 翻译器 API Key
    t_type = translator.get("type", "zhipu")
    if t_type == "zhipu" and not translator.get("api_key"):
        translator["api_key"] = os.environ.get("ZHIPU_API_KEY", "")
    elif t_type == "openai" and not translator.get("api_key"):
        translator["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    elif t_type == "qwen" and not translator.get("api_key"):
        translator["api_key"] = os.environ.get("DASHSCOPE_API_KEY", "")

    # TTS 配置
    tts_type = tts.get("type", "edge")
    if tts_type == "tencent":
        if not tts.get("secret_id"):
            tts["secret_id"] = os.environ.get("TENCENT_SECRET_ID", "")
        if not tts.get("secret_key"):
            tts["secret_key"] = os.environ.get("TENCENT_SECRET_KEY", "")


def validate_config(config: Dict) -> list:
    """验证配置，返回错误列表"""
    errors = []

    # 验证翻译器配置
    t_type = config["translator"].get("type")
    if t_type in ("zhipu", "openai", "qwen"):
        if not config["translator"].get("api_key"):
            errors.append(f"翻译器 {t_type} 需要配置 api_key")

    # 验证 TTS 配置
    tts_type = config["tts"].get("type")
    if tts_type == "tencent":
        if not config["tts"].get("secret_id"):
            errors.append("腾讯云 TTS 需要配置 secret_id")
        if not config["tts"].get("secret_key"):
            errors.append("腾讯云 TTS 需要配置 secret_key")

    return errors
