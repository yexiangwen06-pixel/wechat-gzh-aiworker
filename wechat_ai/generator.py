from .assets import search_assets
from .config import generation_mode_label
from .render import markdown_to_wechat_html


def resolve_generation_mode(api_key: str | None) -> str:
    return "api" if api_key else "simulation"


def build_article_content(conn, payload: dict, api_key: str | None = None, rewrite_hint: str | None = None) -> dict:
    mode = resolve_generation_mode(api_key)
    if mode == "api":
        return build_api_stub(conn, payload, api_key, rewrite_hint)
    return build_simulation_article(conn, payload, rewrite_hint)


def build_api_stub(conn, payload: dict, api_key: str, rewrite_hint: str | None = None) -> dict:
    # MVP 只预留真实模型调用路径，不在没有明确供应商配置时上传素材。
    article = build_simulation_article(conn, payload, rewrite_hint)
    article["generation_mode"] = "api"
    article["generation_mode_label"] = generation_mode_label(api_key)
    article["audit_notes"].insert(0, "当前为真实模型调用预留路径，MVP Demo 使用本地生成结构。")
    return article


def build_simulation_article(conn, payload: dict, rewrite_hint: str | None = None) -> dict:
    content_type = payload.get("content_type", "new_product")
    name = payload.get("product_name") or payload.get("occasion") or "本次主题"
    key_points = payload.get("key_points") or []
    if isinstance(key_points, str):
        key_points = [part.strip() for part in key_points.split(",") if part.strip()]
    query = " ".join([name, *key_points]) or name
    assets = search_assets(conn, query, limit=5)
    image_slots = make_image_slots(assets, payload)
    if content_type == "holiday_campaign":
        title = f"{name}企业饮水活动方案｜限时优惠，健康饮水更省心"
        markdown = holiday_markdown(payload, key_points, assets)
        seo = [name, "节日促销", "企业饮水", "朴道"]
    else:
        title = f"{name}上市｜聚焦企业饮水场景的高效解决方案"
        markdown = product_markdown(payload, key_points, assets)
        seo = [name, "企业直饮机", "健康饮水", "朴道"]
    audit_notes = [
        "模拟生成：请人工核对产品参数、优惠信息和客户案例真实性。",
        "图片为本地素材推荐，发布前需在微信公众号后台手动上传或替换。",
    ]
    if rewrite_hint:
        markdown += f"\n\n### 改写说明\n本版本已按“{rewrite_hint}”方向调整表达，建议发布前再次人工确认。"
        audit_notes.insert(0, f"已执行 AI 改写：{rewrite_hint}")
    html = markdown_to_wechat_html(markdown, image_slots)
    return {
        "title": title,
        "markdown": markdown,
        "html": html,
        "seo_keywords": seo,
        "image_slots": image_slots,
        "audit_notes": audit_notes,
        "generation_mode": "simulation",
        "generation_mode_label": "模拟生成",
    }


def product_markdown(payload: dict, key_points: list[str], assets: list[dict]) -> str:
    name = payload.get("product_name", "新品")
    audience = payload.get("target_audience", "企业用户")
    tone = payload.get("tone", "专业")
    cta = payload.get("cta", "预约企业饮水方案咨询")
    points = key_points or ["高效供水", "稳定水质", "便捷管理"]
    asset_hint = assets[0]["text_excerpt"] if assets and assets[0]["text_excerpt"] else "素材库已记录相关产品资料。"
    bullet_lines = "\n".join(f"- {point}" for point in points)
    return f"""## {name}，为企业饮水效率而来

面向{audience}，朴道希望用更{tone}的方式解决办公、园区、商业空间中的饮水体验问题。

### 核心卖点
{bullet_lines}

### 素材依据
{asset_hint}

### 适用场景
适合办公室、会议空间、企业园区、接待区等需要稳定供水和统一管理的场景。

### 行动召唤
{cta}
"""


def holiday_markdown(payload: dict, key_points: list[str], assets: list[dict]) -> str:
    occasion = payload.get("occasion", "节日活动")
    detail = payload.get("promotion_detail", "企业饮水方案限时优惠")
    deadline = payload.get("deadline", "活动期内")
    cta = payload.get("cta", "联系顾问领取活动方案")
    asset_hint = assets[0]["text_excerpt"] if assets and assets[0]["text_excerpt"] else "素材库已记录节日或促销相关素材。"
    return f"""## {occasion}，给企业饮水方案一个升级理由

节日节点适合做员工关怀、办公体验升级和企业采购方案更新。本次活动聚焦“健康饮水”和“高效服务”。

### 活动信息
{detail}

### 截止时间
{deadline}

### 素材依据
{asset_hint}

### 适用场景
适合企业办公室、园区茶水间、客户接待区和员工福利项目。

### 行动召唤
{cta}
"""


def make_image_slots(assets: list[dict], payload: dict) -> list[dict]:
    images = [asset for asset in assets if asset["type"] == "image"]
    if not images:
        images = assets[:1]
    slots = []
    for idx, asset in enumerate(images[:3], start=1):
        slots.append(
            {
                "position": f"配图{idx}",
                "recommended_asset_path": asset["path"],
                "selected_asset_path": asset["path"],
                "alt_text": f"{payload.get('product_name') or payload.get('occasion') or '文章'}配图",
                "placeholder_text": f"配图占位 {idx}",
            }
        )
    if not slots:
        slots.append(
            {
                "position": "开头配图",
                "recommended_asset_path": "",
                "selected_asset_path": "",
                "alt_text": "待补充配图",
                "placeholder_text": "配图占位：请从素材库补充",
            }
        )
    return slots


def title_candidates(payload: dict) -> list[str]:
    name = payload.get("product_name") or payload.get("occasion") or "企业饮水方案"
    return [
        f"{name}｜企业饮水升级的新选择",
        f"从饮水体验出发，重新认识{name}",
        f"{name}来了：更高效的企业饮水方案",
        f"企业采购关注的饮水方案，{name}这样解决",
        f"{name}｜健康饮水与高效管理兼顾",
    ]
