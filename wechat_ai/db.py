import json
import sqlite3
from pathlib import Path

from .templates import BUILTIN_TEMPLATES


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    if db_path.parent and str(db_path.parent) != ".":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists assets (
            id integer primary key autoincrement,
            path text not null unique,
            type text not null,
            category text not null,
            text_excerpt text not null default '',
            keywords text not null default '[]',
            metadata text not null default '{}',
            created_at text not null default current_timestamp,
            updated_at text not null default current_timestamp
        );

        create table if not exists templates (
            id integer primary key,
            name text not null,
            content_type text not null,
            style_name text not null,
            outline text not null,
            html_style text not null,
            cta_style text not null,
            created_at text not null default current_timestamp,
            updated_at text not null default current_timestamp
        );

        create table if not exists article_jobs (
            id integer primary key autoincrement,
            content_type text not null,
            product_name text not null default '',
            occasion text not null default '',
            key_points text not null default '[]',
            target_audience text not null default '',
            tone text not null default '',
            image_requirement text not null default '',
            cta text not null default '',
            template_id integer references templates(id),
            status text not null default 'generated',
            created_at text not null default current_timestamp,
            updated_at text not null default current_timestamp
        );

        create table if not exists article_versions (
            id integer primary key autoincrement,
            job_id integer not null references article_jobs(id) on delete cascade,
            title text not null,
            markdown text not null,
            html text not null,
            seo_keywords text not null default '[]',
            image_slots text not null default '[]',
            audit_notes text not null default '[]',
            version_type text not null,
            generation_mode text not null,
            created_at text not null default current_timestamp
        );

        create table if not exists image_slots (
            id integer primary key autoincrement,
            article_version_id integer not null references article_versions(id) on delete cascade,
            position text not null,
            recommended_asset_path text not null default '',
            selected_asset_path text not null default '',
            alt_text text not null default '',
            placeholder_text text not null default ''
        );

        create table if not exists quality_scores (
            id integer primary key autoincrement,
            article_version_id integer not null references article_versions(id) on delete cascade,
            overall_score integer not null,
            title_score integer not null,
            structure_score integer not null,
            material_usage_score integer not null,
            compliance_score integer not null,
            readability_score integer not null,
            wechat_format_score integer not null,
            issues text not null default '[]',
            suggestions text not null default '[]',
            scoring_mode text not null default 'rules',
            created_at text not null default current_timestamp
        );
        """
    )
    for template in BUILTIN_TEMPLATES:
        conn.execute(
            """
            insert into templates
                (id, name, content_type, style_name, outline, html_style, cta_style)
            values
                (:id, :name, :content_type, :style_name, :outline, :html_style, :cta_style)
            on conflict(id) do update set
                name=excluded.name,
                content_type=excluded.content_type,
                style_name=excluded.style_name,
                outline=excluded.outline,
                html_style=excluded.html_style,
                cta_style=excluded.cta_style,
                updated_at=current_timestamp
            """,
            template,
        )
    conn.commit()


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
