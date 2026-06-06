from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .assets import list_assets
from .config import generation_mode_label, get_api_key
from .db import connect, init_db
from .service import create_article, get_article, list_articles, optimize_title, replace_image, rewrite_article


def layout(title: str, body: str, api_key: str | None = None) -> str:
    mode = generation_mode_label(api_key)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - 微信公众号内容 AI 工作台</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei",Arial,sans-serif;background:#f5f7fb;color:#182033;}}
    header{{background:#0f4c81;color:white;padding:18px 28px;display:flex;justify-content:space-between;align-items:center;}}
    nav a{{color:white;margin-right:16px;text-decoration:none;font-weight:700;}}
    main{{max-width:1120px;margin:0 auto;padding:28px 20px 48px;}}
    .badge{{display:inline-block;padding:5px 10px;border-radius:999px;background:#fff1c2;color:#7a4b00;font-weight:700;}}
    .card{{background:white;border:1px solid #dbe4ef;border-radius:8px;padding:18px;margin:14px 0;box-shadow:0 8px 24px rgba(16,36,64,.06);}}
    .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}}
    label{{display:block;font-weight:700;margin:10px 0 6px;}}
    input,select,textarea{{width:100%;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:6px;padding:9px;font:inherit;}}
    textarea{{min-height:90px;}}
    button,.btn{{display:inline-block;border:0;background:#0066cc;color:white;border-radius:6px;padding:10px 14px;font-weight:700;text-decoration:none;cursor:pointer;margin:4px 6px 4px 0;}}
    pre{{white-space:pre-wrap;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:6px;overflow:auto;}}
    table{{width:100%;border-collapse:collapse;background:white;}}
    th,td{{border-bottom:1px solid #e2e8f0;padding:10px;text-align:left;vertical-align:top;}}
    .preview{{background:white;padding:18px;border:1px solid #dbe4ef;border-radius:8px;}}
  </style>
</head>
<body>
<header>
  <nav>
    <a href="/">首页</a>
    <a href="/articles/new">新建文章</a>
    <a href="/assets">素材库</a>
    <a href="/templates">模板</a>
  </nav>
  <span class="badge">当前模式：{mode}</span>
</header>
<main>
{body}
</main>
</body>
</html>"""


def render_home_page(conn, api_key: str | None = None) -> str:
    articles = list_articles(conn)
    rows = "".join(
        f"<tr><td>{item['id']}</td><td><a href='/articles/{item['id']}'>{escape(item['title'])}</a></td><td>{item['generation_mode_label']}</td><td>{item['created_at']}</td></tr>"
        for item in articles
    ) or "<tr><td colspan='4'>暂无生成历史，请先新建文章。</td></tr>"
    asset_count = conn.execute("select count(*) from assets").fetchone()[0]
    body = f"""
<h1>首页</h1>
<section class="card">
  <h2>微信公众号内容生成与排版 AI 员工</h2>
  <p>素材库索引：{asset_count} 条。无 API Key 时系统会完整启用 <strong>模拟生成</strong> 流程。</p>
  <a class="btn" href="/articles/new">新建文章</a>
</section>
<section class="card">
  <h2>生成历史</h2>
  <table><tr><th>ID</th><th>标题</th><th>模式</th><th>时间</th></tr>{rows}</table>
</section>"""
    return layout("首页", body, api_key)


def render_new_article_page(conn, api_key: str | None = None) -> str:
    body = """
<h1>新建文章</h1>
<form class="card" method="post" action="/articles/create">
  <div class="grid">
    <div><label>内容类型</label><select name="content_type"><option value="new_product">新品上市</option><option value="holiday_campaign">节日促销</option></select></div>
    <div><label>模板</label><select name="template_id"><option value="1">新品上市模板</option><option value="2">节日促销模板</option><option value="3">简洁品牌模板</option></select></div>
  </div>
  <label>产品名或活动名</label><input name="name" value="名士K2智能直饮机">
  <label>核心卖点或促销信息</label><textarea name="key_points">2000G大流量
DPM动态蛋白纳滤
IoT智能管理</textarea>
  <div class="grid">
    <div><label>目标人群</label><input name="target_audience" value="企业采购决策者"></div>
    <div><label>语气</label><input name="tone" value="专业、科技感"></div>
  </div>
  <label>配图要求</label><input name="image_requirement" value="产品图3张 + 功能示意图">
  <label>CTA</label><input name="cta" value="预约企业饮水方案咨询">
  <button type="submit">生成文章</button>
</form>"""
    return layout("新建文章", body, api_key)


def render_preview_page(conn, job_id: int) -> str:
    article = get_article(conn, job_id)
    latest = article["latest"]
    quality = latest["quality_score"] or {}
    slots = "".join(
        f"<li>{escape(slot.get('position',''))}：{escape(slot.get('selected_asset_path') or slot.get('recommended_asset_path') or '待补充')}</li>"
        for slot in latest["image_slots"]
    )
    audit = "".join(f"<li>{escape(note)}</li>" for note in latest["audit_notes"])
    body = f"""
<h1>文章预览</h1>
<section class="card">
  <span class="badge">{latest['generation_mode_label']}</span>
  <h2>{escape(latest['title'])}</h2>
  <p>质量评分：<strong>{quality.get('overall_score', '-')}</strong> / 100</p>
  <a class="btn" href="/articles/{job_id}/optimize-title">标题优化</a>
  <a class="btn" href="/articles/{job_id}/rewrite">AI改写</a>
  <a class="btn" href="/articles/{job_id}/replace-image">图片替换</a>
  <button onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('html-source').innerText)">一键复制HTML</button>
</section>
<section class="card"><h2>公众号样式预览</h2><div class="preview">{latest['html']}</div></section>
<section class="card"><h2>配图清单</h2><ul>{slots}</ul></section>
<section class="card"><h2>审核要点</h2><ul>{audit}</ul></section>
<section class="card"><h2>Markdown 正文</h2><pre>{escape(latest['markdown'])}</pre></section>
<section class="card"><h2>HTML 源码</h2><pre id="html-source">{escape(latest['html'])}</pre></section>"""
    return layout("文章预览", body, "x" if latest["generation_mode"] == "api" else None)


def render_asset_page(conn) -> str:
    rows = "".join(
        f"<tr><td>{asset['id']}</td><td>{escape(asset['category'])}</td><td>{escape(asset['type'])}</td><td>{escape(asset['path'])}</td><td>{escape(asset['text_excerpt'][:80])}</td></tr>"
        for asset in list_assets(conn)
    ) or "<tr><td colspan='5'>暂无素材，请先运行 reindex。</td></tr>"
    return layout("素材库", f"<h1>素材库</h1><table><tr><th>ID</th><th>分类</th><th>类型</th><th>路径</th><th>摘要</th></tr>{rows}</table>")


def render_template_page(conn) -> str:
    rows = conn.execute("select * from templates order by id").fetchall()
    cards = "".join(
        f"<section class='card'><h2>{escape(row['name'])}</h2><p>内容类型：{escape(row['content_type'])}</p><p>风格：{escape(row['style_name'])}</p><p>CTA：{escape(row['cta_style'])}</p></section>"
        for row in rows
    )
    return layout("模板", f"<h1>模板</h1>{cards}")


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
