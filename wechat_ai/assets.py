import re
import sqlite3
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .db import dumps, loads


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
TEXT_SUFFIXES = {".md", ".txt"}


def detect_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix == ".docx":
        return "docx"
    if suffix == ".pdf":
        return "pdf"
    if suffix in TEXT_SUFFIXES:
        return "markdown" if suffix == ".md" else "text"
    return "unknown"


def infer_category(path: Path, asset_type: str) -> str:
    name = path.name.lower()
    if "logo" in name or "朴道" in path.name:
        return "logo"
    if "海报" in path.name or "促销" in path.name or "节日" in path.name:
        return "海报"
    if "单页" in path.name or "dm" in name:
        return "单页"
    if "解决方案" in path.name:
        return "解决方案"
    if asset_type == "image":
        return "图片"
    if asset_type in {"docx", "pdf", "markdown", "text"}:
        return "文档"
    return "未知"


def extract_text(path: Path, asset_type: str) -> str:
    if asset_type in {"markdown", "text"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if asset_type == "docx":
        return extract_docx_text(path)
    if asset_type == "pdf":
        with path.open("rb") as handle:
            data = handle.read(200_000)
        return data.decode("utf-8", errors="ignore")
    return ""


def extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        return ""
    try:
        root = ElementTree.fromstring(xml)
        return "".join(node.text or "" for node in root.iter() if node.tag.endswith("}t") or node.tag.endswith("t"))
    except ElementTree.ParseError:
        text = xml.decode("utf-8", errors="ignore")
        return " ".join(re.findall(r"<[^:>]*:?t[^>]*>(.*?)</[^:>]*:?t>", text))


def keywords_for(path: Path, text: str) -> list[str]:
    raw = set(re.findall(r"[A-Za-z][A-Za-z0-9]{1,}|[\u4e00-\u9fffA-Za-z0-9]{2,}", path.stem + " " + text))
    preferred: list[str] = []
    joined = path.stem + " " + text
    domain_terms = [
        "K2",
        "H7",
        "P2",
        "直饮机",
        "企业饮水",
        "中央厨房",
        "金融解决方案",
        "节日海报",
        "产品DM",
        "朴道",
        "大流量",
        "动态蛋白纳滤",
        "解决方案",
        "产品单页",
        "促销海报",
    ]
    for term in domain_terms:
        if term in joined and term not in preferred:
            preferred.append(term)
    cleaned = []
    for token in raw:
        if token.isdigit():
            continue
        if len(token) < 2:
            continue
        if re.fullmatch(r"0+[0-9]*", token):
            continue
        if token.lower() in {"pdf", "jpg", "png", "docx", "jpeg"}:
            continue
        if "\ufffd" in token:
            continue
        cleaned.append(token)
    for token in sorted(cleaned):
        if token not in preferred:
            preferred.append(token)
    return preferred[:20]


def index_assets(conn: sqlite3.Connection, root_dir: str | Path) -> int:
    root = Path(root_dir)
    count = 0
    if not root.exists():
        return 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        asset_type = detect_type(path)
        if asset_type == "unknown":
            continue
        text = extract_text(path, asset_type)
        excerpt = " ".join(text.split())[:500]
        metadata = {"size": path.stat().st_size, "suffix": path.suffix.lower()}
        row = {
            "path": str(path),
            "type": asset_type,
            "category": infer_category(path, asset_type),
            "text_excerpt": excerpt,
            "keywords": dumps(keywords_for(path, text)),
            "metadata": dumps(metadata),
        }
        conn.execute(
            """
            insert into assets(path, type, category, text_excerpt, keywords, metadata)
            values(:path, :type, :category, :text_excerpt, :keywords, :metadata)
            on conflict(path) do update set
                type=excluded.type,
                category=excluded.category,
                text_excerpt=excluded.text_excerpt,
                keywords=excluded.keywords,
                metadata=excluded.metadata,
                updated_at=current_timestamp
            """,
            row,
        )
        count += 1
    conn.commit()
    return count


def search_assets(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    like = f"%{query}%"
    rows = conn.execute(
        """
        select * from assets
        where path like ? or text_excerpt like ? or keywords like ?
        order by case when path like ? then 0 else 1 end, id desc
        limit ?
        """,
        (like, like, like, like, limit),
    ).fetchall()
    return [asset_row_to_dict(row) for row in rows]


def list_assets(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    rows = conn.execute("select * from assets order by id desc limit ?", (limit,)).fetchall()
    return [asset_row_to_dict(row) for row in rows]


def asset_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "path": row["path"],
        "type": row["type"],
        "category": row["category"],
        "text_excerpt": row["text_excerpt"],
        "keywords": loads(row["keywords"], []),
        "metadata": loads(row["metadata"], {}),
    }
