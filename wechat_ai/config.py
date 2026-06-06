import os
from pathlib import Path


DEFAULT_DB_PATH = Path(".tmp") / "wechat_ai.db"


def get_api_key() -> str | None:
    """Return configured model API key, if the user explicitly supplied one."""
    return os.environ.get("WECHAT_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def generation_mode_label(api_key: str | None) -> str:
    return "真实模型生成" if api_key else "模拟生成"
