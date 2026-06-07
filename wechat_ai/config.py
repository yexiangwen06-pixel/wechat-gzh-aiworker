import os
from pathlib import Path


DEFAULT_DB_PATH = Path(".tmp") / "wechat_ai.db"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_ENV_PATH = Path(".env")


def load_local_env(path: str | Path = DEFAULT_ENV_PATH, env: dict | None = None, override: bool = True) -> bool:
    """Load KEY=VALUE pairs from a local .env file.

    The desktop workflow uses .env as the source of truth. Overriding stale
    shell variables prevents old WeChat AppSecret values from shadowing edits.
    """
    env = os.environ if env is None else env
    env_path = Path(path)
    if not env_path.exists():
        return False
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in env):
            env[key] = value
    return True


def get_model_provider() -> str:
    """Return the configured article-generation model provider."""
    provider = (os.environ.get("WECHAT_AI_PROVIDER") or os.environ.get("AI_PROVIDER") or "").lower()
    if provider in {"deepseek", "openai"}:
        return provider
    if os.environ.get("DEEPSEEK_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return "deepseek"
    return "openai"


def get_api_key() -> str | None:
    """Return configured model API key, if the user explicitly supplied one."""
    if get_model_provider() == "deepseek":
        return os.environ.get("WECHAT_AI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    return os.environ.get("WECHAT_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def get_model_name() -> str:
    """Return the configured model for article generation."""
    if get_model_provider() == "deepseek":
        return os.environ.get("WECHAT_AI_MODEL") or os.environ.get("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
    return os.environ.get("WECHAT_AI_MODEL") or os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL


def model_runtime_label(api_key: str | None) -> str:
    if not api_key:
        return "模拟生成"
    return f"真实模型生成 · {get_model_provider()}/{get_model_name()}"


def generation_mode_label(api_key: str | None) -> str:
    return "真实模型生成" if api_key else "模拟生成"
