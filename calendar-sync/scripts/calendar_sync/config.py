"""
配置管理 - 加载和解析配置文件，支持环境变量替换
"""

import os
import re
from pathlib import Path
from typing import Optional


def load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件 (YAML)，支持环境变量替换

    优先级: 指定路径 > calendar_sync.yaml > .env 降级
    """
    # 加载 .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    config = {}

    if config_path:
        config = _load_yaml(config_path)
    else:
        # 在常见路径查找配置文件
        candidates = [
            Path("calendar_sync.yaml"),
            Path("config/calendar_sync.yaml"),
            Path(".calendar_sync.yaml"),
        ]
        for p in candidates:
            if p.exists():
                config = _load_yaml(str(p))
                print(f"✓ 使用配置文件: {p}")
                break

    if not config:
        print("⚠ 未找到配置文件，使用环境变量降级配置")
        config = _build_from_env()

    # 替换配置中的环境变量引用
    config = _resolve_env_vars(config)
    return config


def _load_yaml(path: str) -> dict:
    """加载 YAML 文件"""
    try:
        import yaml
    except ImportError:
        raise ImportError("请安装 PyYAML: pip install pyyaml")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_from_env() -> dict:
    """从环境变量构建默认配置（向后兼容旧版 .env 方式）"""
    config = {}

    # 日历源 - 检测可用的源
    if os.getenv("WECOM_CALDAV_USERNAME"):
        config["source"] = {
            "type": "caldav",
            "preset": "wecom",
            "url": os.getenv("WECOM_CALDAV_URL", "https://caldav.wecom.work/calendar/"),
            "username": os.getenv("WECOM_CALDAV_USERNAME", ""),
            "password": os.getenv("WECOM_CALDAV_PASSWORD", ""),
        }
    elif os.getenv("GOOGLE_CALENDAR_CREDENTIALS"):
        config["source"] = {
            "type": "google",
            "credentials_file": os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json"),
        }
    else:
        config["source"] = {"type": "caldav", "preset": "wecom"}

    # AI 分类 - 检测可用的 AI
    if os.getenv("ZHIPU_API_KEY"):
        config["ai"] = {
            "type": "zhipu",
            "api_key": os.getenv("ZHIPU_API_KEY"),
            "model": "glm-4-flash",
        }
    elif os.getenv("OPENAI_API_KEY"):
        config["ai"] = {
            "type": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        }
    elif os.getenv("ANTHROPIC_API_KEY"):
        config["ai"] = {
            "type": "claude",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }
    else:
        config["ai"] = {"type": "keyword"}

    # 笔记输出 - 检测可用的输出
    if os.getenv("NOTION_TOKEN"):
        config["output"] = {
            "type": "notion",
            "token": os.getenv("NOTION_TOKEN"),
            "database_id": os.getenv("NOTION_DATABASE_ID", ""),
        }
    elif os.getenv("OBSIDIAN_VAULT_PATH"):
        config["output"] = {
            "type": "obsidian",
            "vault_path": os.getenv("OBSIDIAN_VAULT_PATH"),
        }
    elif os.getenv("LOGSEQ_GRAPH_PATH"):
        config["output"] = {
            "type": "logseq",
            "graph_path": os.getenv("LOGSEQ_GRAPH_PATH"),
        }
    else:
        config["output"] = {"type": "notion"}

    return config


def _resolve_env_vars(obj):
    """递归替换配置中的 ${ENV_VAR} 引用"""
    if isinstance(obj, str):
        def replacer(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        return re.sub(r"\$\{([^}]+)\}", replacer, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj
