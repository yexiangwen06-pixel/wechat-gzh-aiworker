import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from .assets import list_assets, search_assets
from .config import generation_mode_label, get_model_name, get_model_provider
from .db import dumps
from .render import markdown_to_wechat_html


DEEPSEEK_BLOCKS_SYSTEM_PROMPT = """
你是一名企业微信公众号主编、品牌内容策划师和可视化编辑器内容生成助手。

你的任务是根据用户输入的企业资料、产品信息、卖点、目标受众、语气、CTA和素材摘要，生成一篇可以在前端预览、编辑，并最终保存到微信公众号草稿箱的文章结构。

不要输出 Markdown。
不要输出 HTML。
只输出合法 JSON。

你必须输出结构化 blocks，由前端负责渲染预览，由后端负责转换为微信公众号 HTML。

# 核心要求

1. 内容必须真实可信，优先使用用户提供的企业资料和产品信息。
2. 禁止虚构客户案例、销量、价格、认证、奖项、媒体报道和具体参数。
3. 文章不能写成通用模板，必须围绕用户输入的信息展开。
4. 标题要适合微信公众号阅读场景，抓眼球但不过度标题党。
5. 正文要有公众号阅读节奏，避免大段堆砌。
6. 图片、轮播图、引用卡片、重点信息块都要作为 blocks 输出。
7. 配图关键词必须具体，方便系统从素材库中搜索。
8. 如果素材库可能找不到匹配图片，可以提供 image_generation_prompt 作为兜底。
9. 每篇文章应包含 4~8 个图片相关 blocks，具体数量根据文章长度决定。
10. 至少包含 1 个 gallery 多图组。
11. 不要固定套用“产品介绍-优势-场景-联系我们”的死板结构。

# 输出字段

必须输出以下 JSON：

{
  "title": "",
  "title_options": [],
  "digest": "",
  "cover": {
    "query": "",
    "image_generation_prompt": ""
  },
  "blocks": [],
  "seo_keywords": [],
  "audit_notes": []
}

# block 类型

blocks 中可使用以下类型：

1. heading

用于小标题。

格式：

{
  "type": "heading",
  "level": 2,
  "text": ""
}

2. paragraph

用于普通正文。

格式：

{
  "type": "paragraph",
  "text": ""
}

3. quote

用于重点观点、品牌主张、金句。

格式：

{
  "type": "quote",
  "text": ""
}

4. highlight

用于重点信息卡片。

格式：

{
  "type": "highlight",
  "title": "",
  "items": []
}

5. image

用于单张图片。

格式：

{
  "type": "image",
  "query": "",
  "caption": "",
  "image_generation_prompt": ""
}

6. gallery

用于多图组或轮播图。

格式：

{
  "type": "gallery",
  "queries": [],
  "caption": "",
  "image_generation_prompts": []
}

7. divider

用于分割文章节奏。

格式：

{
  "type": "divider"
}

8. cta

用于结尾行动引导。

格式：

{
  "type": "cta",
  "text": "",
  "button_text": ""
}

# 图片规则

图片是文章体验的一部分，不是装饰。

你需要根据上下文主动安排图片。

图片位置要自然，不能机械地一段文字一张图。

图片关键词要具体，例如：

错误：科技
正确：智能制造车间自动化产线

错误：产品
正确：便携式储能电源户外露营使用场景

优先使用：
企业名称、产品名称、产品外观、产品细节、应用场景、行业场景、团队现场、生产现场。

如果无法确定企业专属素材，则使用行业场景关键词。

# 内容结构要求

根据输入内容自动选择文章结构。

可以是：

- 问题切入型
- 场景故事型
- 新品发布型
- 技术解析型
- 活动宣传型
- 企业品牌型
- 用户痛点解决型

不得每次都使用同一种结构。

# 审核说明 audit_notes

audit_notes 必须说明：

1. 哪些内容直接来自用户输入
2. 哪些内容是基于用户输入的合理扩写
3. 哪些内容发布前建议人工确认
4. 是否存在可能需要企业补充资料的地方

# 输出限制

只返回 JSON。
不要解释。
不要使用 Markdown。
不要使用 HTML。
不要在 JSON 外输出任何文字。
""".strip()


def resolve_generation_mode(api_key: str | None) -> str:
    return "api" if api_key else "simulation"


def build_article_content(conn, payload: dict, api_key: str | None = None, rewrite_hint: str | None = None) -> dict:
    mode = resolve_generation_mode(api_key)
    if mode == "api":
        return build_api_article(conn, payload, api_key, rewrite_hint)
    return build_simulation_article(conn, payload, rewrite_hint)


def build_api_stub(conn, payload: dict, api_key: str, rewrite_hint: str | None = None) -> dict:
    # 只预留真实模型调用路径，不在没有明确供应商配置时上传素材。
    article = build_simulation_article(conn, payload, rewrite_hint)
    article["generation_mode"] = "api"
    article["generation_mode_label"] = generation_mode_label(api_key)
    article["audit_notes"].insert(0, "当前为真实模型调用预留路径；未配置业务模型时使用本地模拟生成结构。")
    return article


def build_api_article(conn, payload: dict, api_key: str, rewrite_hint: str | None = None) -> dict:
    name = payload.get("product_name") or payload.get("occasion") or "本次主题"
    key_points = payload.get("key_points") or []
    if isinstance(key_points, str):
        key_points = [part.strip() for part in key_points.split(",") if part.strip()]
    query = " ".join([name, *key_points]) or name
    assets = search_assets(conn, query, limit=8)
    if not any(asset["type"] == "image" for asset in assets):
        assets = assets + [asset for asset in list_assets(conn, limit=20) if asset["type"] == "image"][:6]
    model = get_model_name()
    provider = get_model_provider()
    if provider == "deepseek":
        generated = call_deepseek_article_api(api_key, model, payload, assets, rewrite_hint)
    else:
        generated = call_openai_article_api(api_key, model, payload, assets, rewrite_hint)
    image_slots = make_image_slots_from_blocks(conn, generated, assets, payload)
    markdown = model_output_to_markdown(generated, payload)
    audit_notes = list(generated.get("audit_notes") or [])
    audit_notes.insert(0, f"真实模型生成：已调用 {provider}/{model} 生成文章正文，请人工核对产品参数和案例真实性。")
    html = markdown_to_wechat_html(markdown, image_slots)
    return {
        "title": generated.get("title") or f"{name}公众号文章",
        "markdown": markdown,
        "html": html,
        "seo_keywords": generated.get("seo_keywords") or [name, "公众号文章"],
        "image_slots": image_slots,
        "audit_notes": audit_notes,
        "blocks": generated.get("blocks") or [],
        "cover": generated.get("cover") or {},
        "digest": generated.get("digest") or "",
        "title_options": generated.get("title_options") or [],
        "generation_mode": "api",
        "generation_mode_label": generation_mode_label(api_key),
    }


def call_openai_article_api(
    api_key: str,
    model: str,
    payload: dict,
    assets: list[dict],
    rewrite_hint: str | None = None,
) -> dict:
    body = {
        "model": model,
        "instructions": (
            "你是企业微信公众号内容运营专家。请根据输入信息生成可直接进入公众号预览的中文文章。"
            "要求：标题清晰，正文适合企业运营人员使用，避免虚构具体认证、客户案例、价格和不可核实参数。"
            "不要输出 HTML，不要插入图片 Markdown；图片由系统素材库自动匹配。只返回符合 JSON Schema 的 JSON。"
        ),
        "input": json.dumps(
            {
                "article_request": payload,
                "rewrite_hint": rewrite_hint,
                "available_materials": summarize_assets_for_model(assets),
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "wechat_article",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "markdown", "seo_keywords", "audit_notes"],
                    "properties": {
                        "title": {"type": "string"},
                        "markdown": {"type": "string"},
                        "seo_keywords": {"type": "array", "items": {"type": "string"}},
                        "audit_notes": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return json.loads(extract_response_text(data))


def call_deepseek_article_api(
    api_key: str,
    model: str,
    payload: dict,
    assets: list[dict],
    rewrite_hint: str | None = None,
) -> dict:
    messages = [
        {
            "role": "system",
            "content": DEEPSEEK_BLOCKS_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "article_request": payload,
                    "rewrite_hint": rewrite_hint,
                    "available_materials": summarize_assets_for_model(assets),
                },
                ensure_ascii=False,
            ),
        },
    ]
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "max_tokens": 4200,
        "temperature": 0.85,
        "stream": False,
    }
    request = Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def extract_response_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"]
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    raise RuntimeError("OpenAI API 未返回文章内容")


def summarize_assets_for_model(assets: list[dict]) -> list[dict]:
    summary = []
    for asset in assets[:10]:
        summary.append(
            {
                "file_name": Path(asset["path"]).name,
                "type": asset["type"],
                "category": asset["category"],
                "keywords": asset.get("keywords", [])[:8],
                "text_excerpt": (asset.get("text_excerpt") or "")[:240],
            }
        )
    return summary


def model_output_to_markdown(generated: dict, payload: dict) -> str:
    blocks = generated.get("blocks") or []
    if not isinstance(blocks, list) or not blocks:
        return normalize_model_markdown(generated.get("markdown", ""), payload)

    title = generated.get("title") or payload.get("product_name") or payload.get("occasion") or "公众号文章"
    lines = [f"## {title}"]
    digest = (generated.get("digest") or "").strip()
    if digest:
        lines.extend(["", digest])

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "heading":
            text = (block.get("text") or "").strip()
            if text:
                try:
                    level = int(block.get("level") or 2)
                except (TypeError, ValueError):
                    level = 2
                prefix = "###" if level >= 3 else "###"
                lines.extend(["", f"{prefix} {text}"])
        elif block_type == "paragraph":
            text = (block.get("text") or "").strip()
            if text:
                lines.extend(["", text])
        elif block_type == "quote":
            text = (block.get("text") or "").strip()
            if text:
                lines.extend(["", f"> {text}"])
        elif block_type == "highlight":
            title_text = (block.get("title") or "重点信息").strip()
            lines.extend(["", f"### {title_text}"])
            for item in block.get("items") or []:
                item_text = str(item).strip()
                if item_text:
                    lines.append(f"- {item_text}")
        elif block_type == "image":
            caption = (block.get("caption") or "").strip()
            query = (block.get("query") or "").strip()
            text = caption or query
            if text:
                lines.extend(["", f"### 配图：{text}"])
        elif block_type == "gallery":
            caption = (block.get("caption") or "多图组").strip()
            lines.extend(["", f"### 图组：{caption}"])
            for query in block.get("queries") or []:
                query_text = str(query).strip()
                if query_text:
                    lines.append(f"- {query_text}")
        elif block_type == "divider":
            lines.extend(["", "### 继续阅读"])
        elif block_type == "cta":
            text = (block.get("text") or "").strip()
            button = (block.get("button_text") or "").strip()
            if text or button:
                lines.extend(["", "### 行动建议"])
                if text:
                    lines.append(text)
                if button:
                    lines.append(f"- {button}")

    return normalize_model_markdown("\n".join(lines), payload)


def make_image_slots_from_blocks(conn, generated: dict, fallback_assets: list[dict], payload: dict) -> list[dict]:
    queries = collect_image_queries(generated)
    if not queries:
        return make_image_slots(fallback_assets, payload)

    positions = ["封面图", "产品图", "参数图", "品牌图"]
    prompts = collect_image_generation_prompts(generated)
    fallback_images = [asset for asset in fallback_assets if asset["type"] == "image"]
    if not fallback_images:
        fallback_images = [asset for asset in list_assets(conn, limit=30) if asset["type"] == "image"]

    used_asset_ids = set()
    slots = []
    for idx, query in enumerate(queries[: len(positions)]):
        asset = best_image_for_query(conn, query, used_asset_ids)
        if not asset and fallback_images:
            asset = fallback_images[idx % len(fallback_images)]
        if not asset:
            prompt = prompts[idx] if idx < len(prompts) else query
            asset = create_generated_prompt_asset(conn, query, prompt)
        if asset:
            used_asset_ids.add(asset.get("id"))
            slots.append(
                {
                    "position": positions[idx],
                    "asset_id": asset.get("id"),
                    "recommended_asset_path": asset["path"],
                    "selected_asset_path": asset["path"],
                    "alt_text": query,
                    "placeholder_text": query,
                }
            )

    if len(slots) < len(positions) and fallback_images:
        for idx in range(len(slots), len(positions)):
            asset = fallback_images[idx % len(fallback_images)]
            slots.append(
                {
                    "position": positions[idx],
                    "asset_id": asset.get("id"),
                    "recommended_asset_path": asset["path"],
                    "selected_asset_path": asset["path"],
                    "alt_text": f"{payload.get('product_name') or payload.get('occasion') or '文章'}配图",
                    "placeholder_text": positions[idx],
                }
            )

    return slots or make_image_slots(fallback_assets, payload)


def collect_image_queries(generated: dict) -> list[str]:
    queries: list[str] = []
    cover = generated.get("cover") or {}
    if isinstance(cover, dict) and cover.get("query"):
        queries.append(str(cover["query"]).strip())
    blocks = generated.get("blocks") or []
    if not isinstance(blocks, list):
        return queries
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "image" and block.get("query"):
            queries.append(str(block["query"]).strip())
        elif block.get("type") == "gallery":
            for query in block.get("queries") or []:
                queries.append(str(query).strip())
    cleaned = []
    for query in queries:
        if query and query not in cleaned:
            cleaned.append(query)
    return cleaned


def collect_image_generation_prompts(generated: dict) -> list[str]:
    prompts: list[str] = []
    cover = generated.get("cover") or {}
    if isinstance(cover, dict) and cover.get("image_generation_prompt"):
        prompts.append(str(cover["image_generation_prompt"]).strip())
    blocks = generated.get("blocks") or []
    if not isinstance(blocks, list):
        return prompts
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "image" and block.get("image_generation_prompt"):
            prompts.append(str(block["image_generation_prompt"]).strip())
        elif block.get("type") == "gallery":
            for prompt in block.get("image_generation_prompts") or []:
                prompts.append(str(prompt).strip())
    return [prompt for prompt in prompts if prompt]


def create_generated_prompt_asset(conn, query: str, prompt: str) -> dict:
    target_dir = Path(".tmp") / "generated_images"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", query).strip("_") or "ai_image"
    target = target_dir / f"{safe_stem[:48]}.svg"
    counter = 1
    while target.exists():
        target = target_dir / f"{safe_stem[:42]}_{counter}.svg"
        counter += 1
    target.write_text(generated_prompt_svg(query, prompt), encoding="utf-8")
    metadata = {"generated": True, "source": "image_generation_prompt"}
    row = {
        "path": str(target),
        "type": "image",
        "category": "AI生成图",
        "text_excerpt": prompt,
        "keywords": dumps([word for word in [query, prompt, "AI生成图"] if word]),
        "metadata": dumps(metadata),
    }
    conn.execute(
        """
        insert into assets(path, type, category, text_excerpt, keywords, metadata)
        values(:path, :type, :category, :text_excerpt, :keywords, :metadata)
        on conflict(path) do update set
            text_excerpt=excluded.text_excerpt,
            keywords=excluded.keywords,
            metadata=excluded.metadata,
            updated_at=current_timestamp
        """,
        row,
    )
    conn.commit()
    saved = conn.execute("select * from assets where path = ?", (str(target),)).fetchone()
    return {
        "id": saved["id"],
        "path": saved["path"],
        "type": saved["type"],
        "category": saved["category"],
        "text_excerpt": saved["text_excerpt"],
        "keywords": json.loads(saved["keywords"]),
        "metadata": json.loads(saved["metadata"]),
    }


def generated_prompt_svg(query: str, prompt: str) -> str:
    def esc(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    prompt_lines = wrap_svg_text(prompt or query, 24)[:5]
    text_spans = "\n".join(
        f"<text x='72' y='{210 + idx * 34}' font-size='24' fill='#334155'>{esc(line)}</text>"
        for idx, line in enumerate(prompt_lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#e7f2ff"/>
    <stop offset="0.52" stop-color="#eefaf8"/>
    <stop offset="1" stop-color="#ffffff"/>
  </linearGradient>
</defs>
<rect width="1200" height="675" fill="url(#bg)"/>
<rect x="48" y="48" width="1104" height="579" rx="28" fill="rgba(255,255,255,.74)" stroke="#b8c7dc" stroke-width="2"/>
<circle cx="1020" cy="164" r="76" fill="#1264d8" opacity=".12"/>
<circle cx="1075" cy="228" r="42" fill="#0f9f8f" opacity=".18"/>
<text x="72" y="122" font-size="34" font-weight="800" fill="#0f3768">AI 配图建议</text>
<text x="72" y="166" font-size="22" fill="#0f766e">{esc(query)}</text>
{text_spans}
<rect x="72" y="520" width="250" height="54" rx="12" fill="#1264d8"/>
<text x="105" y="555" font-size="24" font-weight="800" fill="#ffffff">待接入真实图片模型</text>
</svg>"""


def wrap_svg_text(text: str, size: int) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    return [text[idx : idx + size] for idx in range(0, len(text), size)]


def best_image_for_query(conn, query: str, used_asset_ids: set[int | None]) -> dict | None:
    candidates = [asset for asset in search_assets(conn, query, limit=8) if asset["type"] == "image"]
    for asset in candidates:
        if asset.get("id") not in used_asset_ids:
            return asset
    parts = [part.strip() for part in query.replace("，", " ").replace(",", " ").split() if len(part.strip()) >= 2]
    for part in parts:
        candidates = [asset for asset in search_assets(conn, part, limit=6) if asset["type"] == "image"]
        for asset in candidates:
            if asset.get("id") not in used_asset_ids:
                return asset
    return None


def normalize_model_markdown(markdown: str, payload: dict) -> str:
    markdown = (markdown or "").strip()
    if not markdown:
        name = payload.get("product_name") or payload.get("occasion") or "本次主题"
        return f"## {name}\n\n请补充正文内容。"
    if not markdown.startswith("#"):
        markdown = "## 公众号文章正文\n\n" + markdown
    return markdown


def build_simulation_article(conn, payload: dict, rewrite_hint: str | None = None) -> dict:
    content_type = payload.get("content_type", "new_product")
    name = payload.get("product_name") or payload.get("occasion") or "本次主题"
    key_points = payload.get("key_points") or []
    if isinstance(key_points, str):
        key_points = [part.strip() for part in key_points.split(",") if part.strip()]
    query = " ".join([name, *key_points]) or name
    assets = search_assets(conn, query, limit=8)
    if not any(asset["type"] == "image" for asset in assets):
        assets = assets + [asset for asset in list_assets(conn) if asset["type"] == "image"][:6]
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
    positions = ["封面图", "产品图", "参数图", "品牌图"]
    slots = []
    if images:
        while len(images) < len(positions):
            images.append(images[len(images) % len(images)])
    for idx, asset in enumerate(images[: len(positions)]):
        slots.append(
            {
                "position": positions[idx],
                "asset_id": asset.get("id"),
                "recommended_asset_path": asset["path"],
                "selected_asset_path": asset["path"],
                "alt_text": f"{payload.get('product_name') or payload.get('occasion') or '文章'}配图",
                "placeholder_text": positions[idx],
            }
        )
    if not slots:
        for position in positions:
            slots.append(
                {
                    "position": position,
                    "recommended_asset_path": "",
                    "selected_asset_path": "",
                    "alt_text": f"{position}待补充",
                    "placeholder_text": position,
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
