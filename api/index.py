import os
from pathlib import Path
import sys
import threading


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wechat_ai.assets import index_assets
from wechat_ai.config import get_api_key, load_local_env
from wechat_ai.db import connect, init_db
from wechat_ai.web import WorkbenchHandler


_CONN = None
_CONN_LOCK = threading.Lock()


def _load_environment() -> None:
    if not os.environ.get("VERCEL"):
        load_local_env(ROOT / ".env")
    os.environ.setdefault("WECHAT_AI_UPLOAD_DIR", "/tmp/wechat_ai_uploads")


def _db_path() -> Path:
    return Path(os.environ.get("WECHAT_AI_VERCEL_DB", "/tmp/wechat_ai_vercel.db"))


def get_vercel_connection():
    global _CONN
    if _CONN is None:
        with _CONN_LOCK:
            if _CONN is None:
                _load_environment()
                conn = connect(_db_path())
                init_db(conn)
                index_assets(conn, ROOT / "demo_assets")
                _CONN = conn
    return _CONN


def configure_server(server):
    _load_environment()
    server.conn = get_vercel_connection()
    server.api_key = get_api_key()
    return server


class handler(WorkbenchHandler):
    def __init__(self, *args, **kwargs):
        if len(args) >= 3:
            configure_server(args[2])
        super().__init__(*args, **kwargs)
