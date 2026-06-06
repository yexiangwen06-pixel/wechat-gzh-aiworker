ABSOLUTE_WORDS = ["最好", "第一", "顶级", "唯一", "最强"]


def check_title(title: str) -> list[str]:
    return [word for word in ABSOLUTE_WORDS if word in title]


def score_article(title: str, markdown: str, html: str, image_slots: list[dict], audit_notes: list[str]) -> dict:
    issues: list[str] = []
    suggestions: list[str] = []
    title_score = 90
    risky = check_title(title)
    if risky:
        title_score -= 30
        issues.append("标题包含广告法高风险词：" + "、".join(risky))
        suggestions.append("替换绝对化表达，改为具体卖点或场景价值。")
    word_count = len(markdown)
    readability_score = 85 if 300 <= word_count <= 1800 else 70
    if word_count < 300:
        issues.append("正文偏短，建议补充场景痛点和产品价值。")
    structure_score = 90 if "###" in markdown else 75
    material_usage_score = 85 if image_slots else 65
    if not image_slots:
        suggestions.append("建议至少推荐 1-3 张配图。")
    compliance_score = 88 if not risky else 60
    wechat_format_score = 90 if "<section" in html and "style=" in html else 65
    if audit_notes:
        suggestions.extend(audit_notes[:2])
    overall = round(
        (
            title_score
            + structure_score
            + material_usage_score
            + compliance_score
            + readability_score
            + wechat_format_score
        )
        / 6
    )
    return {
        "overall_score": overall,
        "title_score": title_score,
        "structure_score": structure_score,
        "material_usage_score": material_usage_score,
        "compliance_score": compliance_score,
        "readability_score": readability_score,
        "wechat_format_score": wechat_format_score,
        "issues": issues,
        "suggestions": suggestions or ["文章结构完整，可进入人工审核。"],
        "scoring_mode": "rules",
    }
