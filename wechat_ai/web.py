from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .assets import list_assets
from .config import generation_mode_label, get_api_key
from .db import connect, init_db, loads
from .service import create_article, get_article, list_articles, optimize_title, replace_image, rewrite_article


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
    @media (max-width:900px){{.hero,.preview-grid,.form-grid{{grid-template-columns:1fr}}.metrics,.cards,.asset-grid,.wizard{{grid-template-columns:1fr}}}}
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
  <p>像和一位内容 AI 员工协作：先定类型，再输入素材线索，选择风格，最后生成可预览文章。</p>
</section>
<section class="wizard">
  <div class="wizard-step"><h3>1 选择内容类型</h3><p>新品上市或节日促销，决定文章结构。</p></div>
  <div class="wizard-step"><h3>2 填写内容</h3><p>输入产品、活动、卖点、语气和 CTA。</p></div>
  <div class="wizard-step"><h3>3 选择风格模板</h3><p>专业科技、促销活动或简洁品牌。</p></div>
  <div class="wizard-step"><h3>4 生成</h3><p>AI 自动匹配素材并生成预览。</p></div>
</section>
<form class="surface" method="post" action="/articles/create">
  <div class="form-grid">
    <div><label>内容类型</label><select name="content_type"><option value="new_product">新品上市</option><option value="holiday_campaign">节日促销</option></select></div>
    <div><label>风格模板</label><select name="template_id"><option value="1">专业科技风 · 新品上市模板</option><option value="2">促销活动风 · 节日促销模板</option><option value="3">简洁品牌风 · 品牌模板</option></select></div>
  </div>
  <label>产品名或活动名</label><input name="name" value="名士K2智能直饮机">
  <label>核心卖点或促销信息</label><textarea name="key_points">2000G大流量
DPM动态蛋白纳滤
IoT智能管理</textarea>
  <div class="form-grid">
    <div><label>目标人群</label><input name="target_audience" value="企业采购决策者"></div>
    <div><label>语气</label><input name="tone" value="专业、科技感"></div>
  </div>
  <label>配图要求</label><input name="image_requirement" value="产品图3张 + 功能示意图">
  <label>CTA</label><input name="cta" value="预约企业饮水方案咨询">
  <button type="submit">生成</button>
</form>"""
    return layout("新建文章", body, api_key)


def render_preview_page(conn, job_id: int) -> str:
    article = get_article(conn, job_id)
    latest = article["latest"]
    quality = latest["quality_score"] or {}
    slots = "".join(
        f"<li><strong>{escape(slot.get('position',''))}</strong>：{escape(Path(slot.get('selected_asset_path') or slot.get('recommended_asset_path') or '待补充').name)}</li>"
        for slot in latest["image_slots"]
    )
    audit = "".join(f"<li>{escape(note)}</li>" for note in latest["audit_notes"])
    suggestions = "".join(f"<span class='chip'>{escape(item)}</span>" for item in quality.get("suggestions", [])[:3])
    body = f"""
<section class="hero">
  <div class="surface">
    <p class="muted">文章预览 · 智能匹配结果</p>
    <h1>{escape(latest['title'])}</h1>
    <p>AI 已完成素材匹配、结构生成、公众号样式渲染和质量评分。</p>
    <button onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('html-source').innerText)">一键复制HTML</button>
    <a class="btn secondary" href="/articles/{job_id}/optimize-title">标题优化</a>
    <a class="btn secondary" href="/articles/{job_id}/rewrite">AI改写</a>
    <a class="btn secondary" href="/articles/{job_id}/replace-image">图片替换</a>
  </div>
  <aside class="ai-panel">
    <div class="ai-state"><strong>AI状态面板</strong><span class="badge {'real' if latest['generation_mode'] == 'api' else 'simulation'}">{latest['generation_mode_label']}</span></div>
    <div class="score">{quality.get('overall_score', '-')}</div>
    <p>文章质量评分 / 100</p>
    <div class="recommend">推荐内容提示：{suggestions or '建议检查配图和 CTA 后复制 HTML。'}</div>
  </aside>
</section>
<section class="preview-grid">
  <div class="surface"><h2>公众号样式预览</h2><div class="preview">{latest['html']}</div></div>
  <div>
    <section class="surface"><h2>智能匹配结果</h2><p>配图清单</p><ul>{slots}</ul></section>
    <section class="surface"><h2>审核要点</h2><ul>{audit}</ul></section>
  </div>
</section>
<section class="surface"><h2>Markdown 正文</h2><pre>{escape(latest['markdown'])}</pre></section>
<section class="surface"><h2>HTML 源码</h2><pre id="html-source">{escape(latest['html'])}</pre></section>"""
    return layout("文章预览", body, "x" if latest["generation_mode"] == "api" else None)


def render_asset_page(conn) -> str:
    assets = list_assets(conn)
    cards = "".join(render_asset_card(asset) for asset in assets) or "<p>暂无素材，请先运行 reindex。</p>"
    body = f"""
<section class="surface">
  <p class="muted">素材分析进度 · 素材卡片</p>
  <h1>素材库</h1>
  <p>卡片只展示可用于创作的信息，不暴露本地文件路径。</p>
</section>
<section class="asset-grid">{cards}</section>"""
    return layout("素材库", body)


def render_asset_card(asset: dict) -> str:
    name = Path(asset["path"]).name
    keywords = asset.get("keywords", [])[:4]
    chips = "".join(f"<span class='chip'>{escape(word)}</span>" for word in keywords) or "<span class='chip'>待分析</span>"
    thumb = (
        f"<img alt='图片缩略图' src='/asset-thumb/{asset['id']}'>"
        if asset["type"] == "image"
        else f"<span>图片缩略图<br>{escape(asset['type'].upper())}</span>"
    )
    return f"""
<article class="asset-card">
  <div class="thumb">{thumb}</div>
  <h3>{escape(name)}</h3>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
  <p><strong>关键词</strong>：{chips}</p>
  <p><strong>推荐用途</strong>：{escape(recommended_use(asset))}</p>
</article>"""


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
    return layout("模板", f"<section class='surface'><p class='muted'>模板工作台</p><h1>模板</h1><p>每个模板都带有公众号样式预览，方便答辩展示不同风格。</p></section><section class='cards'>{cards}</section>")


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
            elif parsed.path == "/articles/new":
                self.respond(render_new_article_page(conn, self.server.api_key))
            elif parsed.path == "/assets":
                self.respond(render_asset_page(conn))
            elif parsed.path == "/templates":
                self.respond(render_template_page(conn))
            elif parsed.path.startswith("/asset-thumb/"):
                self.respond_asset_thumb(conn, int(parsed.path.rsplit("/", 1)[-1]))
            elif parsed.path.endswith("/optimize-title"):
                job_id = int(parsed.path.split("/")[2])
                optimize_title(conn, job_id, self.server.api_key)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.endswith("/rewrite"):
                job_id = int(parsed.path.split("/")[2])
                rewrite_article(conn, job_id, "更简洁", self.server.api_key)
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.endswith("/replace-image"):
                job_id = int(parsed.path.split("/")[2])
                replace_image(conn, job_id, 0, "手动替换：请在素材库选择新图片")
                self.redirect(f"/articles/{job_id}")
            elif parsed.path.startswith("/articles/"):
                self.respond(render_preview_page(conn, int(parsed.path.split("/")[2])))
            else:
                self.send_error(404, "页面不存在")
        except Exception as exc:
            self.send_error(500, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/articles/create":
            self.send_error(404, "页面不存在")
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
            self.send_error(404, "缩略图不存在")
            return
        data = Path(row["path"]).read_bytes()
        suffix = Path(row["path"]).suffix.lower().lstrip(".") or "jpeg"
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
