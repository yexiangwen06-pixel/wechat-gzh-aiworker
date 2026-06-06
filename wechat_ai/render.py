import html
from pathlib import Path
from urllib.parse import quote


def markdown_to_wechat_html(markdown: str, image_slots: list[dict] | None = None) -> str:
    image_slots = image_slots or []
    title, paragraphs, sections = parse_markdown(markdown)
    banner = slot_by_position(image_slots, "封面图") or first_slot(image_slots)
    product = slot_by_position(image_slots, "产品图") or first_slot(image_slots)
    case = slot_by_position(image_slots, "案例图") or first_slot(image_slots)
    first_para = paragraphs[0] if paragraphs else "围绕企业真实饮水场景，结合素材库自动生成公众号文章。"
    parts = [
        '<section style="max-width:677px;margin:0 auto;padding:0 0 20px;color:#1f2937;font-size:16px;line-height:1.85;background:#ffffff;">',
        render_image(banner, "Banner图", wide=True),
        f'<h1 style="font-size:24px;line-height:1.35;text-align:center;color:#0f3768;margin:24px 18px 12px;font-weight:800;">{html.escape(title)}</h1>',
        '<section style="width:48px;height:4px;background:#1264d8;border-radius:99px;margin:0 auto 22px;"></section>',
        f'<blockquote style="margin:0 18px 22px;padding:14px 16px;border-left:4px solid #0f9f8f;background:#eefaf8;color:#334155;border-radius:6px;"><strong>引用块</strong><br>{html.escape(first_para)}</blockquote>',
        '<section style="margin:0 18px 22px;display:block;">',
        render_image(product, "产品图", wide=False),
        '<section style="margin-top:12px;">',
    ]
    for heading, body_lines in sections[:3]:
        parts.append(f'<h2 style="font-size:18px;color:#1264d8;margin:18px 0 8px;">{html.escape(heading)}</h2>')
        for line in body_lines:
            if line.startswith("- "):
                parts.append(f'<p style="margin:6px 0;padding-left:10px;">• {html.escape(line[2:])}</p>')
            else:
                parts.append(f'<p style="margin:8px 0;text-align:justify;">{html.escape(line)}</p>')
    parts.extend(
        [
            "</section></section>",
            '<section style="height:1px;background:#dbe3ef;margin:22px 18px;"></section>',
            '<section style="margin:0 18px 22px;display:block;">',
            render_image(case, "案例图", wide=False),
            '<p style="margin:12px 0;text-align:justify;">图片+文字混排：AI 会把素材库图片与正文段落组合展示，运营人员可在预览页继续替换图片。</p>',
            "</section>",
            '<section style="margin:24px 18px 0;padding:14px 18px;background:#1264d8;color:#fff;text-align:center;border-radius:8px;font-weight:800;">CTA按钮：点击阅读原文或联系顾问，获取企业定制方案</section>',
            "</section>",
        ]
    )
    return "\n".join(parts)


def parse_markdown(markdown: str) -> tuple[str, list[str], list[tuple[str, list[str]]]]:
    title = "公众号文章"
    paragraphs: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            title = line[3:]
        elif line.startswith("### "):
            if current_heading:
                sections.append((current_heading, current_lines))
            current_heading = line[4:]
            current_lines = []
        else:
            if current_heading:
                current_lines.append(line)
            else:
                paragraphs.append(line)
    if current_heading:
        sections.append((current_heading, current_lines))
    return title, paragraphs, sections


def slot_by_position(slots: list[dict], position: str) -> dict | None:
    for slot in slots:
        if slot.get("position") == position:
            return slot
    return None


def first_slot(slots: list[dict]) -> dict | None:
    for slot in slots:
        if slot.get("selected_asset_path") or slot.get("recommended_asset_path"):
            return slot
    return None


def render_image(slot: dict | None, label: str, wide: bool) -> str:
    path = ""
    alt = label
    if slot:
        asset_id = slot.get("asset_id")
        path = slot.get("selected_asset_path") or slot.get("recommended_asset_path") or ""
        alt = slot.get("alt_text") or label
    else:
        asset_id = None
    if slot and asset_id:
        src = f"/asset-thumb/{asset_id}"
        radius = "8px" if wide else "7px"
        return (
            f'<figure style="margin:0 0 12px;text-align:center;">'
            f'<img src="{src}" alt="{html.escape(alt)}" style="width:100%;max-height:{360 if wide else 260}px;object-fit:cover;border-radius:{radius};display:block;">'
            f'<figcaption style="font-size:13px;color:#64748b;margin-top:6px;">{label}</figcaption>'
            f"</figure>"
        )
    if path and Path(path).exists():
        src = "/asset-file?path=" + quote(path)
        radius = "8px" if wide else "7px"
        return (
            f'<figure style="margin:0 0 12px;text-align:center;">'
            f'<img src="{src}" alt="{html.escape(alt)}" style="width:100%;max-height:{360 if wide else 260}px;object-fit:cover;border-radius:{radius};display:block;">'
            f'<figcaption style="font-size:13px;color:#64748b;margin-top:6px;">{label}</figcaption>'
            f"</figure>"
        )
    return (
        f'<section style="margin:0 0 12px;padding:14px;border:1px dashed #9bb5d7;border-radius:8px;background:#f6f9ff;color:#48627f;text-align:center;">'
        f"{label}：未匹配到图片，已在预览页显示推荐素材列表</section>"
    )
