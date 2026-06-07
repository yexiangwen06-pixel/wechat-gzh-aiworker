import sqlite3

from .config import generation_mode_label
from .db import dumps, loads
from .generator import build_article_content, model_output_to_markdown, title_candidates
from .quality import score_article
from .render import markdown_to_wechat_html


def create_article(conn: sqlite3.Connection, payload: dict, api_key: str | None = None) -> dict:
    template_id = int(payload.get("template_id") or default_template_id(payload))
    job_row = {
        "content_type": payload.get("content_type", "new_product"),
        "product_name": payload.get("product_name", ""),
        "occasion": payload.get("occasion", ""),
        "key_points": dumps(payload.get("key_points", [])),
        "target_audience": payload.get("target_audience", ""),
        "tone": payload.get("tone", ""),
        "image_requirement": payload.get("image_requirement", ""),
        "cta": payload.get("cta", ""),
        "template_id": template_id,
    }
    cur = conn.execute(
        """
        insert into article_jobs
            (content_type, product_name, occasion, key_points, target_audience, tone,
             image_requirement, cta, template_id)
        values
            (:content_type, :product_name, :occasion, :key_points, :target_audience, :tone,
             :image_requirement, :cta, :template_id)
        """,
        job_row,
    )
    job_id = cur.lastrowid
    article = build_article_content(conn, payload, api_key)
    article["job_id"] = job_id
    article["version_id"] = save_version(conn, job_id, article, "initial")
    conn.commit()
    return article


def save_version(conn: sqlite3.Connection, job_id: int, article: dict, version_type: str) -> int:
    cur = conn.execute(
        """
        insert into article_versions
            (job_id, title, markdown, html, seo_keywords, image_slots, audit_notes,
             blocks, cover, digest, title_options, version_type, generation_mode)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            article["title"],
            article["markdown"],
            article["html"],
            dumps(article.get("seo_keywords", [])),
            dumps(article.get("image_slots", [])),
            dumps(article.get("audit_notes", [])),
            dumps(article.get("blocks", [])),
            dumps(article.get("cover", {})),
            article.get("digest", ""),
            dumps(article.get("title_options", [])),
            version_type,
            article.get("generation_mode", "simulation"),
        ),
    )
    version_id = cur.lastrowid
    for slot in article.get("image_slots", []):
        conn.execute(
            """
            insert into image_slots
                (article_version_id, position, recommended_asset_path, selected_asset_path,
                 alt_text, placeholder_text)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                slot.get("position", ""),
                slot.get("recommended_asset_path", ""),
                slot.get("selected_asset_path", ""),
                slot.get("alt_text", ""),
                slot.get("placeholder_text", ""),
            ),
        )
    quality = score_article(
        article["title"],
        article["markdown"],
        article["html"],
        article.get("image_slots", []),
        article.get("audit_notes", []),
    )
    conn.execute(
        """
        insert into quality_scores
            (article_version_id, overall_score, title_score, structure_score,
             material_usage_score, compliance_score, readability_score, wechat_format_score,
             issues, suggestions, scoring_mode)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            quality["overall_score"],
            quality["title_score"],
            quality["structure_score"],
            quality["material_usage_score"],
            quality["compliance_score"],
            quality["readability_score"],
            quality["wechat_format_score"],
            dumps(quality["issues"]),
            dumps(quality["suggestions"]),
            quality["scoring_mode"],
        ),
    )
    article["quality_score"] = quality
    return version_id


def default_template_id(payload: dict) -> int:
    return 2 if payload.get("content_type") == "holiday_campaign" else 1


def list_articles(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        select j.*, v.title, v.generation_mode
        from article_jobs j
        left join article_versions v on v.id = (
            select id from article_versions where job_id = j.id order by id desc limit 1
        )
        order by j.id desc
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"] or "未命名文章",
            "content_type": row["content_type"],
            "generation_mode": row["generation_mode"] or "simulation",
            "generation_mode_label": generation_mode_label("x" if row["generation_mode"] == "api" else None),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_article(conn: sqlite3.Connection, job_id: int) -> dict:
    job = conn.execute("select * from article_jobs where id = ?", (job_id,)).fetchone()
    if not job:
        raise KeyError(f"文章任务不存在：{job_id}")
    version_rows = conn.execute(
        "select * from article_versions where job_id = ? order by id",
        (job_id,),
    ).fetchall()
    versions = [version_to_dict(conn, row) for row in version_rows]
    return {
        "job": dict(job),
        "versions": versions,
        "latest": versions[-1] if versions else None,
    }


def version_to_dict(conn: sqlite3.Connection, row) -> dict:
    quality_row = conn.execute(
        "select * from quality_scores where article_version_id = ? order by id desc limit 1",
        (row["id"],),
    ).fetchone()
    quality = None
    if quality_row:
        quality = {
            "overall_score": quality_row["overall_score"],
            "title_score": quality_row["title_score"],
            "structure_score": quality_row["structure_score"],
            "material_usage_score": quality_row["material_usage_score"],
            "compliance_score": quality_row["compliance_score"],
            "readability_score": quality_row["readability_score"],
            "wechat_format_score": quality_row["wechat_format_score"],
            "issues": loads(quality_row["issues"], []),
            "suggestions": loads(quality_row["suggestions"], []),
            "scoring_mode": quality_row["scoring_mode"],
        }
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "title": row["title"],
        "markdown": row["markdown"],
        "html": row["html"],
        "seo_keywords": loads(row["seo_keywords"], []),
        "image_slots": loads(row["image_slots"], []),
        "audit_notes": loads(row["audit_notes"], []),
        "blocks": loads(row["blocks"], []),
        "cover": loads(row["cover"], {}),
        "digest": row["digest"],
        "title_options": loads(row["title_options"], []),
        "version_type": row["version_type"],
        "generation_mode": row["generation_mode"],
        "generation_mode_label": generation_mode_label("x" if row["generation_mode"] == "api" else None),
        "quality_score": quality,
        "created_at": row["created_at"],
    }


def optimize_title(conn: sqlite3.Connection, job_id: int, api_key: str | None = None) -> list[str]:
    article = get_article(conn, job_id)
    payload = article_payload(article["job"])
    titles = title_candidates(payload)
    latest = article["latest"]
    updated = dict(latest)
    updated["title"] = titles[0]
    updated["audit_notes"] = ["已生成 5 个标题候选，请选择最适合本次投放目标的标题。"] + latest["audit_notes"]
    updated["generation_mode"] = "api" if api_key else "simulation"
    save_version(conn, job_id, updated, "title_optimized")
    conn.commit()
    return titles


def adopt_title(conn: sqlite3.Connection, job_id: int, title: str, api_key: str | None = None) -> dict:
    article = get_article(conn, job_id)
    latest = dict(article["latest"])
    latest["title"] = title
    latest["audit_notes"] = [f"已采用标题：{title}"] + latest["audit_notes"]
    latest["generation_mode"] = "api" if api_key else "simulation"
    latest["version_id"] = save_version(conn, job_id, latest, "title_optimized")
    conn.commit()
    return latest


def rewrite_article(conn: sqlite3.Connection, job_id: int, rewrite_hint: str, api_key: str | None = None) -> dict:
    article = get_article(conn, job_id)
    payload = article_payload(article["job"])
    rewritten = build_article_content(conn, payload, api_key, rewrite_hint=rewrite_hint)
    rewritten["job_id"] = job_id
    rewritten["version_id"] = save_version(conn, job_id, rewritten, "rewrite")
    conn.commit()
    return rewritten


def save_blocks(conn: sqlite3.Connection, job_id: int, blocks: list[dict], api_key: str | None = None) -> dict:
    article = get_article(conn, job_id)
    latest = dict(article["latest"])
    payload = article_payload(article["job"])
    generated = {
        "title": latest["title"],
        "digest": latest.get("digest", ""),
        "blocks": blocks,
    }
    latest["blocks"] = blocks
    latest["markdown"] = model_output_to_markdown(generated, payload)
    latest["html"] = markdown_to_wechat_html(latest["markdown"], latest.get("image_slots", []))
    latest["audit_notes"] = ["已保存 blocks 编辑内容，并重新生成微信公众号 HTML。"] + latest["audit_notes"]
    latest["generation_mode"] = "api" if api_key else latest.get("generation_mode", "simulation")
    latest["version_id"] = save_version(conn, job_id, latest, "blocks_edited")
    conn.commit()
    return latest


def replace_image(conn: sqlite3.Connection, job_id: int, slot_index: int, selected_asset_path: str) -> dict:
    article = get_article(conn, job_id)
    latest = dict(article["latest"])
    slots = [dict(slot) for slot in latest["image_slots"]]
    if not slots:
        slots.append(
            {
                "position": "配图1",
                "recommended_asset_path": "",
                "selected_asset_path": selected_asset_path,
                "alt_text": "替换配图",
                "placeholder_text": "推荐候选图片 1",
            }
        )
    else:
        selected = slots[min(slot_index, len(slots) - 1)]
        selected["selected_asset_path"] = selected_asset_path
        row = conn.execute("select id from assets where path = ?", (selected_asset_path,)).fetchone()
        if row:
            selected["asset_id"] = row["id"]
    latest["image_slots"] = slots
    latest["html"] = markdown_to_wechat_html(latest["markdown"], slots)
    latest["audit_notes"] = ["已替换图片占位，请在公众号后台上传对应图片。"] + latest["audit_notes"]
    latest["version_id"] = save_version(conn, job_id, latest, "image_replaced")
    conn.commit()
    return latest


def article_payload(job_row) -> dict:
    return {
        "content_type": job_row["content_type"],
        "product_name": job_row["product_name"],
        "occasion": job_row["occasion"],
        "key_points": loads(job_row["key_points"], []),
        "target_audience": job_row["target_audience"],
        "tone": job_row["tone"],
        "image_requirement": job_row["image_requirement"],
        "cta": job_row["cta"],
        "template_id": job_row["template_id"],
    }
