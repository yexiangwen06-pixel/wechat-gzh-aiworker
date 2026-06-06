import html


def markdown_to_wechat_html(markdown: str, image_slots: list[dict] | None = None) -> str:
    image_slots = image_slots or []
    lines = markdown.splitlines()
    parts = [
        "<section style=\"max-width:677px;margin:0 auto;padding:8px 0;color:#1f2937;font-size:16px;line-height:1.85;\">"
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            parts.append("<p style=\"height:8px;margin:0;\"></p>")
        elif stripped.startswith("## "):
            parts.append(
                f"<h2 style=\"font-size:22px;color:#0066cc;text-align:center;margin:24px 0 14px;\">{html.escape(stripped[3:])}</h2>"
            )
        elif stripped.startswith("### "):
            parts.append(
                f"<h3 style=\"font-size:18px;color:#0f766e;border-left:4px solid #0f766e;padding-left:10px;margin:22px 0 10px;\">{html.escape(stripped[4:])}</h3>"
            )
        elif stripped.startswith("- "):
            parts.append(
                f"<p style=\"margin:8px 0;padding-left:14px;\">• {html.escape(stripped[2:])}</p>"
            )
        else:
            parts.append(f"<p style=\"margin:12px 0;text-align:justify;\">{html.escape(stripped)}</p>")
    for slot in image_slots:
        placeholder = html.escape(slot.get("placeholder_text", "配图占位"))
        alt = html.escape(slot.get("alt_text", "公众号配图"))
        path = html.escape(slot.get("selected_asset_path") or slot.get("recommended_asset_path") or "")
        parts.append(
            "<section style=\"margin:18px 0;padding:14px;border:1px dashed #7aa7d9;border-radius:6px;background:#f5f9ff;text-align:center;\">"
            f"<strong>{placeholder}</strong><br><span style=\"font-size:13px;color:#64748b;\">{alt}</span><br>"
            f"<span style=\"font-size:12px;color:#94a3b8;\">{path}</span></section>"
        )
    parts.append(
        "<section style=\"margin:24px 0;padding:14px 18px;background:#0066cc;color:#fff;text-align:center;border-radius:6px;font-weight:bold;\">点击阅读原文或联系顾问，获取企业定制方案</section>"
    )
    parts.append("</section>")
    return "\n".join(parts)
