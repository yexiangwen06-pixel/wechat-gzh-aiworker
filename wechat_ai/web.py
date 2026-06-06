from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from .assets import list_assets
from .config import generation_mode_label, get_api_key
from .db import connect, init_db, loads
from .generator import title_candidates
from .service import (
    adopt_title,
    article_payload,
    create_article,
    get_article,
    list_articles,
    optimize_title,
    replace_image,
    rewrite_article,
)


def layout(title: str, body: str, api_key: str | None = None) -> str:
    mode = generation_mode_label(api_key)
    mode_class = "real" if api_key else "simulation"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - 微信公众号内容 AI 工作台</title>
  <style>
    :root {{
      --ink:#162033; --muted:#637083; --line:#dbe3ef; --panel:#fff;
      --bg:#f4f7fb; --blue:#1264d8; --teal:#0f9f8f; --amber:#b36b00; --rose:#c2415b;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif;background:var(--bg);color:var(--ink);}}
    header{{position:sticky;top:0;z-index:2;background:rgba(255,255,255,.92);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);}}
    .topbar{{max-width:1180px;margin:0 auto;padding:14px 22px;display:flex;align-items:center;justify-content:space-between;gap:18px;}}
    .brand{{display:flex;align-items:center;gap:10px;font-weight:800;}}
    .mark{{width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,var(--blue),var(--teal));display:grid;place-items:center;color:#fff;}}
    nav a{{color:#334155;text-decoration:none;font-weight:700;margin:0 8px;padding:8px 10px;border-radius:6px;}}
    nav a:hover{{background:#eef4ff;color:var(--blue);}}
    main{{max-width:1180px;margin:0 auto;padding:28px 22px 54px;}}
    h1{{font-size:30px;line-height:1.25;margin:0 0 8px;letter-spacing:0;}}
    h2{{font-size:20px;margin:0 0 10px;letter-spacing:0;}}
    h3{{font-size:16px;margin:0 0 8px;letter-spacing:0;}}
    p{{color:var(--muted);line-height:1.7;margin:0 0 10px;}}
    .hero{{display:grid;grid-template-columns:1.5fr .9fr;gap:18px;margin-bottom:18px;align-items:stretch;}}
    .surface,.metric,.article-card,.asset-card,.template-card,.wizard-step,.ai-panel{{background:var(--panel);border:1px solid var(--line);border-radius:8px;box-shadow:0 14px 34px rgba(23,40,72,.07);}}
    .surface{{padding:22px;}}
    .ai-panel{{padding:18px;background:linear-gradient(135deg,#ffffff,#eef8f6);}}
    .ai-state{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;}}
    .pulse{{width:11px;height:11px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 6px rgba(15,159,143,.12);}}
    .badge{{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;font-size:13px;font-weight:800;}}
    .badge.simulation{{background:#fff3cf;color:#7a4b00;}}
    .badge.real{{background:#dff8ef;color:#08735f;}}
    .btn,button{{display:inline-flex;align-items:center;justify-content:center;min-height:38px;border:0;border-radius:6px;background:var(--blue);color:#fff;font-weight:800;text-decoration:none;padding:10px 14px;cursor:pointer;margin:4px 6px 4px 0;}}
    .btn.secondary{{background:#eef4ff;color:var(--blue);}}
    .btn.teal{{background:var(--teal);}}
    .metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:18px 0;}}
    .metric{{padding:18px;}}
    .metric strong{{display:block;font-size:30px;color:var(--ink);margin-top:8px;}}
    .progress{{height:9px;background:#e8eef7;border-radius:999px;overflow:hidden;margin-top:10px;}}
    .progress span{{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--teal));}}
    .cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;}}
    .article-card,.asset-card,.template-card{{padding:16px;}}
    .article-card a{{color:var(--ink);text-decoration:none;}}
    .muted{{color:var(--muted);font-size:13px;}}
    .chip{{display:inline-flex;margin:3px 4px 3px 0;padding:4px 8px;border-radius:999px;background:#eef4ff;color:#2457a6;font-size:12px;font-weight:700;}}
    .wizard{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0;}}
    .wizard-step{{padding:14px;border-top:4px solid var(--blue);}}
    .step-block{{padding:18px;margin:14px 0;border-left:5px solid var(--blue);}}
    .option-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:10px;}}
    .option-card{{border:1px solid var(--line);border-radius:8px;padding:14px;background:#fbfdff;cursor:pointer;}}
    .option-card input{{width:auto;margin-right:8px;}}
    form.surface{{margin-top:14px;}}
    label{{display:block;font-weight:800;margin:12px 0 6px;}}
    input,select,textarea{{width:100%;border:1px solid #cbd5e1;border-radius:6px;padding:10px;font:inherit;background:#fff;}}
    textarea{{min-height:110px;resize:vertical;}}
    .form-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}}
    .preview-grid{{display:grid;grid-template-columns:1.05fr .95fr;gap:16px;align-items:start;}}
    .preview{{background:#fff;padding:18px;border:1px solid var(--line);border-radius:8px;max-height:640px;overflow:auto;}}
    pre{{white-space:pre-wrap;background:#101827;color:#e2e8f0;padding:14px;border-radius:6px;overflow:auto;}}
    .score{{font-size:38px;font-weight:900;color:var(--teal);}}
    .asset-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}}
    .thumb{{height:124px;border-radius:7px;background:#eef3f8;display:grid;place-items:center;overflow:hidden;margin-bottom:12px;color:#536273;font-weight:800;}}
    .thumb img{{width:100%;height:100%;object-fit:cover;display:block;}}
    .template-preview{{border:1px solid var(--line);border-radius:8px;background:#fff;padding:12px;margin-top:12px;}}
    .wechat-mini{{max-width:290px;margin:0 auto;border-radius:8px;border:1px solid #d9e2ef;padding:14px;background:#fbfdff;}}
    .wechat-mini .title{{font-weight:900;color:var(--blue);text-align:center;margin-bottom:10px;}}
    .wechat-mini .line{{height:8px;background:#e6edf6;border-radius:999px;margin:8px 0;}}
    .wechat-mini .cta{{background:var(--blue);color:#fff;border-radius:6px;text-align:center;padding:8px;margin-top:10px;font-weight:800;}}
    .recommend{{border-left:4px solid var(--teal);padding:10px 12px;background:#eefaf8;border-radius:6px;margin:10px 0;}}
    .workflow{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;margin:0 0 18px;}}
    .workflow span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:8px;text-align:center;font-size:12px;font-weight:800;color:#42526a;}}
    .workflow .active{{background:#e9f7f5;color:#08735f;border-color:#8fd8cc;}}
    .drawer{{position:relative;background:#fff;border:1px solid var(--line);border-radius:8px;padding:16px;margin-bottom:14px;box-shadow:0 14px 34px rgba(23,40,72,.07);}}
    .candidate{{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid #edf2f7;padding:10px 0;}}
    .candidate:last-child{{border-bottom:0;}}
    .style-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;}}
    .version-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}}
    .version-box{{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fbfdff;max-height:260px;overflow:auto;}}
    .image-slot-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}}
    .image-slot-card{{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fff;}}
    .selector-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px;}}
    .selector-item{{border:1px solid var(--line);border-radius:8px;padding:8px;background:#fbfdff;}}
    .asset-card,.option-card,.template-card,.article-card,.image-slot-card{{transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;}}
    .asset-card:hover,.option-card:hover,.template-card:hover,.article-card:hover,.image-slot-card:hover{{transform:translateY(-3px);box-shadow:0 18px 42px rgba(23,40,72,.12);border-color:#b8c7dc;}}
    .btn:hover,button:hover{{transform:translateY(-1px);filter:brightness(1.03);}}
    main{{animation:fadeIn .22s ease both;}}
    @keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
    .asset-drawer{{display:none;position:fixed;right:22px;top:86px;width:min(440px,calc(100vw - 44px));max-height:calc(100vh - 112px);overflow:auto;background:rgba(255,255,255,.94);backdrop-filter:blur(16px);border:1px solid var(--line);border-radius:8px;box-shadow:0 24px 80px rgba(15,23,42,.22);z-index:4;padding:18px;}}
    .asset-drawer:target{{display:block;animation:slideIn .2s ease both;}}
    @keyframes slideIn{{from{{opacity:0;transform:translateX(24px)}}to{{opacity:1;transform:none}}}}
    .pdf-card{{height:124px;border-radius:7px;background:linear-gradient(135deg,#fff7ed,#fee2e2);display:grid;place-items:center;margin-bottom:12px;color:#9f1239;font-weight:900;text-align:center;}}
    @media (max-width:900px){{.hero,.preview-grid,.form-grid,.version-grid{{grid-template-columns:1fr}}.metrics,.cards,.asset-grid,.wizard,.option-grid,.style-grid,.image-slot-grid,.selector-grid,.workflow{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <div class="topbar">
    <div class="brand"><div class="mark">AI</div><span>公众号内容 AI 员工</span></div>
    <nav>
      <a href="/">Dashboard</a>
      <a href="/articles/new">新建文章</a>
      <a href="/assets">素材库</a>
      <a href="/templates">模板</a>
    </nav>
    <span class="badge {mode_class}">{mode}</span>
  </div>
</header>
<main>{body}</main>
</body>
</html>"""


def render_home_page(conn, api_key: str | None = None) -> str:
    articles = list_articles(conn)
    asset_count = conn.execute("select count(*) from assets").fetchone()[0]
    template_count = conn.execute("select count(*) from templates").fetchone()[0]
    article_count = conn.execute("select count(*) from article_jobs").fetchone()[0]
    progress = min(100, 35 + asset_count * 3)
    recent_cards = "".join(
        f"""
        <article class="article-card">
          <p class="muted">最近生成文章 · {escape(item['generation_mode_label'])}</p>
          <h3><a href="/articles/{item['id']}">{escape(item['title'])}</a></h3>
          <p>智能匹配结果已保存，可继续标题优化、AI改写或复制 HTML。</p>
          <a class="btn secondary" href="/articles/{item['id']}">打开预览</a>
        </article>
        """
        for item in articles[:6]
    ) or '<article class="article-card"><h3>还没有文章</h3><p>从快速创建开始，让 AI 员工生成第一篇公众号内容。</p></article>'
    body = f"""
<section class="hero">
  <div class="surface">
    <p class="muted">AI 工作台 Dashboard</p>
    <h1>让公众号内容从素材库自动长出来</h1>
    <p>AI 员工会读取企业素材、匹配模板、生成文章、给出质量评分，并把结果整理成可复制到微信公众号后台的 HTML。</p>
    <a class="btn" href="/articles/new">快速创建</a>
    <a class="btn secondary" href="/assets">查看素材分析</a>
  </div>
  <aside class="ai-panel">
    <div class="ai-state"><strong>AI状态面板</strong><span class="pulse"></span></div>
    <p>当前模式：<strong>{generation_mode_label(api_key)}</strong></p>
    <p>素材分析进度</p>
    <div class="progress"><span style="width:{progress}%"></span></div>
    <p class="recommend">推荐内容提示：优先使用“新品上市模板”生成 K2 产品推广，再用标题优化生成 5 个候选标题。</p>
  </aside>
</section>
<section class="metrics">
  <div class="metric"><span class="muted">素材数量</span><strong>{asset_count}</strong><p>已进入本地索引</p></div>
  <div class="metric"><span class="muted">模板数量</span><strong>{template_count}</strong><p>支持多风格切换</p></div>
  <div class="metric"><span class="muted">文章生成数量</span><strong>{article_count}</strong><p>沉淀为历史记录</p></div>
</section>
<section class="surface">
  <h2>最近生成文章</h2>
  <div class="cards">{recent_cards}</div>
</section>"""
    return layout("AI 工作台 Dashboard", body, api_key)


def render_new_article_page(conn, api_key: str | None = None) -> str:
    body = """
<section class="surface">
  <p class="muted">向导式流程</p>
  <h1>新建公众号文章</h1>
  <p>像和一位内容 AI 员工协作：按 Step1 到 Step4 完成一次内容生成，而不是填写数据库表单。</p>
</section>
<form class="surface" method="post" action="/articles/create">
  <section class="surface step-block">
    <p class="muted">Step1 选择内容类型</p>
    <h2>内容类型卡片</h2>
    <div class="option-grid">
      <label class="option-card"><input type="radio" name="content_type" value="new_product" checked><strong>新品上市</strong><p>突出产品卖点、技术亮点和企业采购价值。</p></label>
      <label class="option-card"><input type="radio" name="content_type" value="holiday_campaign"><strong>节日促销</strong><p>突出活动节点、优惠信息和咨询转化。</p></label>
      <label class="option-card"><input type="radio" name="content_type" value="new_product"><strong>品牌科普</strong><p>暂用新品模板，适合沉淀品牌知识和产品认知。</p></label>
    </div>
  </section>
  <section class="surface step-block">
    <p class="muted">Step2 填写内容</p>
    <h2>告诉 AI 员工这次要写什么</h2>
    <label>产品名或活动名</label><input name="name" value="名士K2智能直饮机">
    <label>核心卖点或促销信息</label><textarea name="key_points">2000G大流量
DPM动态蛋白纳滤
IoT智能管理</textarea>
    <div class="form-grid">
      <div><label>目标人群</label><input name="target_audience" value="企业采购决策者"></div>
      <div><label>语气</label><input name="tone" value="专业、科技感"></div>
    </div>
    <label>配图要求</label><input name="image_requirement" value="封面图 + 产品图 + 案例图">
    <label>CTA</label><input name="cta" value="预约企业饮水方案咨询">
  </section>
  <section class="surface step-block">
    <p class="muted">Step3 选择风格模板</p>
    <h2>选择公众号排版和表达风格</h2>
    <div class="option-grid">
      <label class="option-card"><input type="radio" name="template_id" value="1" checked><strong>专业科技风</strong><p>适合新品上市、参数讲解和企业采购。</p></label>
      <label class="option-card"><input type="radio" name="template_id" value="2"><strong>促销活动风</strong><p>适合节日节点、限时优惠和活动转化。</p></label>
      <label class="option-card"><input type="radio" name="template_id" value="3"><strong>简洁品牌风</strong><p>适合品牌形象、服务介绍和轻量推文。</p></label>
    </div>
  </section>
  <section class="surface step-block">
    <p class="muted">Step4 生成文章</p>
    <h2>生成后进入优化工作流</h2>
    <p>AI 将自动匹配素材库图片，生成接近公众号最终效果的预览，并进入标题优化、AI改写、图片调整和最终确认流程。</p>
    <div class="recommend">生成中 AI 正在分析素材：产品图、参数图、品牌图会自动进入文章预览。</div>
    <button type="submit">生成文章</button>
  </section>
</form>"""
    return layout("新建文章", body, api_key)


def render_preview_page(conn, job_id: int) -> str:
    article = get_article(conn, job_id)
    latest = article["latest"]
    original = article["versions"][0] if article["versions"] else latest
    rewritten = next((version for version in reversed(article["versions"]) if version["version_type"] == "rewrite"), None)
    quality = latest["quality_score"] or {}
    audit = "".join(f"<li>{escape(note)}</li>" for note in latest["audit_notes"])
    suggestions = "".join(f"<span class='chip'>{escape(item)}</span>" for item in quality.get("suggestions", [])[:3])
    payload = article_payload(article["job"])
    candidates = title_candidates(payload)
    image_assets = [asset for asset in list_assets(conn, limit=80) if asset["type"] == "image"]
    body = f"""
{render_workflow()}
<section class="hero">
  <div class="surface">
    <p class="muted">文章预览 · 智能匹配结果</p>
    <h1>{escape(latest['title'])}</h1>
    <p>AI 已完成生成，接下来按工作流完成标题优化、AI改写、图片调整、最终确认和复制HTML。</p>
    <div class="recommend">已应用新标题后会立即更新文章标题；当前页面保留全部候选标题供运营选择。</div>
    <button onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('html-source').innerText)">一键复制HTML</button>
    <a class="btn secondary" href="#title-drawer">标题优化</a>
    <a class="btn secondary" href="#rewrite-drawer">AI改写</a>
    <a class="btn secondary" href="#image-drawer">图片调整</a>
  </div>
  <aside class="ai-panel">
    <div class="ai-state"><strong>AI状态面板</strong><span class="badge {'real' if latest['generation_mode'] == 'api' else 'simulation'}">{latest['generation_mode_label']}</span></div>
    <div class="score">{quality.get('overall_score', '-')}</div>
    <p>文章质量评分 / 100</p>
    <div class="recommend">推荐内容提示：{suggestions or '建议检查配图和 CTA 后复制 HTML。'}</div>
  </aside>
</section>
{render_title_drawer(job_id, candidates)}
{render_rewrite_drawer(job_id, original, rewritten)}
{render_image_drawer(job_id, latest["image_slots"], image_assets)}
<section class="preview-grid">
  <div class="surface"><h2>公众号样式预览</h2><div class="preview">{latest['html']}</div></div>
  <div>
    <section class="surface"><h2>当前文章已使用的图片清单</h2>{render_used_image_list(latest["image_slots"])}</section>
    <section class="surface"><h2>最终确认</h2><p>确认标题、正文、图片和 CTA 后，点击复制HTML。复制前建议在公众号后台再预览一次。</p><button onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('html-source').innerText)">复制HTML</button></section>
    <section class="surface"><h2>审核要点</h2><ul>{audit}</ul></section>
  </div>
</section>
<section class="surface"><h2>Markdown 正文</h2><pre>{escape(latest['markdown'])}</pre></section>
<details class="surface"><summary><strong>HTML源码</strong></summary><pre id="html-source">{escape(latest['html'])}</pre></details>"""
    return layout("文章预览", body, "x" if latest["generation_mode"] == "api" else None)


def render_workflow() -> str:
    steps = ["创建", "生成", "标题优化", "AI改写", "图片调整", "最终确认", "复制HTML"]
    return '<section class="workflow">' + "".join(f'<span class="active">{step}</span>' for step in steps) + "</section>"


def render_title_drawer(job_id: int, candidates: list[str]) -> str:
    rows = "".join(
        f"""
        <div class="candidate">
          <div><strong>标题候选{idx}</strong><p>{escape(title)}</p></div>
          <a class="btn secondary" href="/articles/{job_id}/adopt-title?title={quote(title)}">采用</a>
        </div>
        """
        for idx, title in enumerate(candidates, start=1)
    )
    return f'<section id="title-drawer" class="drawer"><h2>标题优化</h2><p>点击“采用”即可切换标题。</p>{rows}</section>'


def render_rewrite_drawer(job_id: int, original: dict, rewritten: dict | None) -> str:
    styles = ["更专业", "更营销", "更亲和", "更简洁", "更有科技感"]
    links = "".join(f'<a class="btn secondary" href="/articles/{job_id}/rewrite?style={quote(style)}">{style}</a>' for style in styles)
    rewritten_markdown = rewritten["markdown"] if rewritten else "尚未生成改写版本，请先选择一种改写风格。"
    return f"""
<section id="rewrite-drawer" class="drawer">
  <h2>AI改写</h2>
  <p>请选择改写风格：</p>
  <div class="style-grid">{links}</div>
  <div class="version-grid" style="margin-top:12px;">
    <div class="version-box"><h3>原版本</h3><pre>{escape(original['markdown'])}</pre></div>
    <div class="version-box"><h3>改写版本</h3><pre>{escape(rewritten_markdown)}</pre></div>
  </div>
  <a class="btn teal" href="/articles/{job_id}/rewrite?style=采用改写版">采用改写版</a>
  <a class="btn secondary" href="/articles/{job_id}">保留原文</a>
</section>"""


def render_image_drawer(job_id: int, slots: list[dict], image_assets: list[dict]) -> str:
    slot_cards = "".join(render_image_slot_card(job_id, idx, slot, image_assets) for idx, slot in enumerate(slots))
    if not image_assets:
        selector = '<p>未找到可用图片。推荐素材列表为空，请先在素材库中补充图片。</p>'
    else:
        selector = "".join(render_selector_item(asset) for asset in image_assets[:8])
    return f"""
<section id="image-drawer" class="drawer">
  <h2>图片调整</h2>
  <p>生成文章后自动显示封面图、产品图、参数图、品牌图。案例图可在素材库选择器中继续补充。每个图片位都可以从素材库选择器中替换。</p>
  <div class="image-slot-grid">{slot_cards}</div>
  <h3 style="margin-top:16px;">素材库选择器</h3>
  <div class="selector-grid">{selector}</div>
</section>"""


def render_image_slot_card(job_id: int, idx: int, slot: dict, image_assets: list[dict]) -> str:
    selected = slot.get("selected_asset_path") or slot.get("recommended_asset_path") or ""
    asset_id = asset_id_for_path(image_assets, selected)
    thumb = (
        f'<img alt="{escape(slot.get("position", "图片"))}" src="/asset-thumb/{asset_id}">'
        if asset_id
        else "<span>推荐素材列表</span>"
    )
    first_replacement = quote(image_assets[0]["path"]) if image_assets else ""
    return f"""
<article class="image-slot-card">
  <h3>{escape(slot.get('position', f'图片位{idx + 1}'))}</h3>
  <div class="thumb">{thumb}</div>
  <p class="muted">当前推荐图片缩略图</p>
  <a class="btn secondary" href="/articles/{job_id}/replace-image?slot={idx}&path={first_replacement}">更换图片</a>
</article>"""


def render_used_image_list(slots: list[dict]) -> str:
    items = "".join(
        f"<li>{escape(slot.get('position', '图片'))}：{escape(Path(slot.get('selected_asset_path') or slot.get('recommended_asset_path') or '推荐候选图片').name)}</li>"
        for slot in slots
    )
    return f"<ul>{items}</ul>"


def render_selector_item(asset: dict) -> str:
    return f"""
<article class="selector-item">
  <div class="thumb"><img alt="素材缩略图" src="/asset-thumb/{asset['id']}"></div>
  <p>{escape(Path(asset['path']).name)}</p>
</article>"""


def asset_id_for_path(image_assets: list[dict], path: str) -> int | None:
    for asset in image_assets:
        if asset["path"] == path:
            return int(asset["id"])
    return None


def render_asset_page(conn) -> str:
    assets = list_assets(conn)
    cards = "".join(render_asset_card(asset) for asset in assets) or "<p>暂无素材，请先运行 reindex。</p>"
    drawers = "".join(render_asset_drawer(asset) for asset in assets)
    body = f"""
<section class="surface">
  <p class="muted">素材分析进度 · 素材卡片</p>
  <h1>素材库</h1>
  <p>卡片只展示可用于创作的信息，不暴露本地文件路径。点击素材可查看详情，并加入文章、作为封面或作为正文配图。</p>
</section>
<section class="surface">
  <h2>搜索与筛选</h2>
  <div class="form-grid">
    <label>搜索素材<input placeholder="搜索素材：K2、直饮机、节日海报、金融解决方案"></label>
    <label>分类筛选<select><option>全部</option><option>产品图</option><option>海报</option><option>logo</option><option>PDF</option><option>解决方案</option><option>案例</option><option>单页</option></select></label>
    <label>用途筛选<select><option>全部用途</option><option>封面图</option><option>正文配图</option><option>品牌区</option><option>参数资料</option></select></label>
  </div>
</section>
<section class="asset-grid">{cards}</section>
{drawers}"""
    return layout("素材库", body)


def render_asset_card(asset: dict) -> str:
    name = Path(asset["path"]).name
    keywords = asset.get("keywords", [])[:4]
    chips = "".join(f"<span class='chip'>{escape(word)}</span>" for word in keywords) or "<span class='chip'>待分析</span>"
    thumb = asset_visual(asset, small=True)
    return f"""
<a class="asset-card" href="#asset-{asset['id']}" style="display:block;text-decoration:none;color:inherit;">
  <div class="thumb">{thumb}</div>
  <h3>{escape(name)}</h3>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
  <p><strong>关键词</strong>：{chips}</p>
  <p><strong>推荐用途</strong>：{escape(recommended_use(asset))}</p>
</a>"""


def asset_visual(asset: dict, small: bool = False) -> str:
    if asset["type"] == "image":
        return f"<img alt='大图预览' src='/asset-thumb/{asset['id']}'>"
    if asset["type"] == "pdf":
        return "<div class='pdf-card'>PDF资料卡<br><span style='font-size:13px;color:#9f1239;'>第一页缩略图待生成</span></div>"
    return f"<span>{escape(asset['type'].upper())}</span>"


def render_asset_drawer(asset: dict) -> str:
    name = Path(asset["path"]).name
    keywords = "".join(f"<span class='chip'>{escape(word)}</span>" for word in asset.get("keywords", [])[:8]) or "<span class='chip'>待分析</span>"
    page_count = asset.get("metadata", {}).get("pages") or "待解析"
    pdf_meta = f"<p><strong>页数</strong>：{page_count}</p>" if asset["type"] == "pdf" else ""
    return f"""
<aside id="asset-{asset['id']}" class="asset-drawer">
  <a href="#" class="btn secondary" style="float:right;">关闭</a>
  <h2>素材详情</h2>
  <div class="thumb" style="height:220px;">{asset_visual(asset)}</div>
  <h3>大图预览</h3>
  <p><strong>文件名</strong>：{escape(name)}</p>
  <p><strong>文件类型</strong>：{escape(asset['type'])}</p>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
  {pdf_meta}
  <p><strong>关键词</strong>：{keywords}</p>
  <p><strong>推荐用途</strong>：{escape(recommended_use(asset))}</p>
  <a class="btn" href="#">加入文章</a>
  <a class="btn secondary" href="#">作为封面</a>
  <a class="btn secondary" href="#">作为正文配图</a>
</aside>"""


def recommended_use(asset: dict) -> str:
    category = asset["category"]
    if category == "海报":
        return "适合作为节日促销封面或正文氛围图"
    if category == "单页":
        return "适合提取产品参数和卖点"
    if category == "logo":
        return "适合放在文章页首或页尾品牌区"
    if asset["type"] == "image":
        return "适合作为文章配图候选"
    return "适合作为文案生成素材依据"


def render_template_page(conn) -> str:
    rows = conn.execute("select * from templates order by id").fetchall()
    cards = "".join(render_template_card(row) for row in rows)
    return layout("模板", f"<section class='surface'><p class='muted'>模板工作台</p><h1>模板</h1><p>每个模板都带有公众号样式预览，方便运营人员快速切换不同内容风格。</p></section><section class='cards'>{cards}</section>")


def render_template_card(row) -> str:
    outline = loads(row["outline"], [])
    outline_chips = "".join(f"<span class='chip'>{escape(item)}</span>" for item in outline[:4])
    return f"""
<article class="template-card">
  <h2>{escape(row['name'])}</h2>
  <p>风格：{escape(row['style_name'])}</p>
  <p>{outline_chips}</p>
  <div class="template-preview">
    <h3>公众号样式预览</h3>
    <div class="wechat-mini">
      <div class="title">{escape(row['style_name'])}</div>
      <div class="line" style="width:88%"></div>
      <div class="line" style="width:72%"></div>
      <div class="line" style="width:94%"></div>
      <div class="cta">{escape(row['cta_style'])}</div>
    </div>
  </div>
</article>"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        conn = self.server.conn
        try:
            if parsed.path == "/":
                self.respond(render_home_page(conn, self.server.api_key))
            elif parsed.path == "/new":
                self.redirect("/articles/new")
            elif parsed.path == "/articles/new":
                self.respond(render_new_article_page(conn, self.server.api_key))
            elif parsed.path == "/assets":
                self.respond(render_asset_page(conn))
            elif parsed.path == "/templates":
                self.respond(render_template_page(conn))
            elif parsed.path.startswith("/asset-thumb/"):
                self.respond_asset_thumb(conn, int(parsed.path.rsplit("/", 1)[-1]))
            elif parsed.path == "/asset-file":
                query = parse_qs(parsed.query)
                self.respond_asset_file(unquote(query.get("path", [""])[0]))
            elif parsed.path.endswith("/optimize-title"):
                job_id = int(parsed.path.split("/")[2])
                optimize_title(conn, job_id, self.server.api_key)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.endswith("/adopt-title"):
                job_id = int(parsed.path.split("/")[2])
                query = parse_qs(parsed.query)
                adopt_title(conn, job_id, query.get("title", [""])[0], self.server.api_key)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.endswith("/rewrite"):
                job_id = int(parsed.path.split("/")[2])
                query = parse_qs(parsed.query)
                rewrite_article(conn, job_id, query.get("style", ["更简洁"])[0], self.server.api_key)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.endswith("/replace-image"):
                job_id = int(parsed.path.split("/")[2])
                query = parse_qs(parsed.query)
                slot = int(query.get("slot", ["0"])[0])
                path = query.get("path", [""])[0] or "手动替换：请在素材库选择新图片"
                replace_image(conn, job_id, slot, path)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.startswith("/articles/"):
                self.respond(render_preview_page(conn, int(parsed.path.split("/")[2])))
            else:
                self.send_error(404, "Not found")
        except Exception as exc:
            self.send_error(500, "Server error")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/articles/create":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        content_type = data.get("content_type", ["new_product"])[0]
        name = data.get("name", [""])[0]
        payload = {
            "content_type": content_type,
            "product_name": name if content_type == "new_product" else "",
            "occasion": name if content_type == "holiday_campaign" else "",
            "key_points": data.get("key_points", [""])[0].splitlines(),
            "promotion_detail": data.get("key_points", [""])[0],
            "target_audience": data.get("target_audience", [""])[0],
            "tone": data.get("tone", [""])[0],
            "image_requirement": data.get("image_requirement", [""])[0],
            "cta": data.get("cta", [""])[0],
            "template_id": int(data.get("template_id", ["1"])[0]),
        }
        article = create_article(self.server.conn, payload, self.server.api_key)
        self.redirect(f"/articles/{article['job_id']}")

    def respond(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_asset_thumb(self, conn, asset_id: int):
        row = conn.execute("select path, type from assets where id = ?", (asset_id,)).fetchone()
        if not row or row["type"] != "image" or not Path(row["path"]).exists():
            self.respond_svg_placeholder("image")
            return
        data = Path(row["path"]).read_bytes()
        suffix = Path(row["path"]).suffix.lower().lstrip(".") or "jpeg"
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_asset_file(self, path: str):
        file_path = Path(path)
        if not path or not file_path.exists() or file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            self.respond_svg_placeholder("image")
            return
        data = file_path.read_bytes()
        suffix = file_path.suffix.lower().lstrip(".") or "jpeg"
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_svg_placeholder(self, label: str):
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='480'>"
            "<rect width='100%' height='100%' fill='#eef3f8'/>"
            "<text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' "
            "font-family='Arial' font-size='28' fill='#64748b'>"
            f"{escape(label)}</text></svg>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(svg)))
        self.end_headers()
        self.wfile.write(svg)

    def redirect(self, path: str):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()


def run_server(db_path, host: str = "127.0.0.1", port: int = 8765):
    conn = connect(db_path)
    init_db(conn)
    server = ThreadingHTTPServer((host, port), WorkbenchHandler)
    server.conn = conn
    server.api_key = get_api_key()
    print(f"微信公众号内容 AI 工作台已启动：http://localhost:{port}")
    print(f"当前生成模式：{generation_mode_label(server.api_key)}")
    server.serve_forever()
