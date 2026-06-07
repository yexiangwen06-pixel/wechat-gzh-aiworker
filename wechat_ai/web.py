from html import escape
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, quote, unquote, urlparse

from .assets import IMAGE_SUFFIXES, index_assets, list_assets
from .config import generation_mode_label, get_api_key, get_model_name, get_model_provider, load_local_env, model_runtime_label
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
    save_blocks,
)
from .wechat_draft import WeChatDraftError, WeChatDraftService


def layout(title: str, body: str, api_key: str | None = None) -> str:
    mode = model_runtime_label(api_key)
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
    body{{margin:0;font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif;background:
      radial-gradient(circle at 12% 8%,rgba(18,100,216,.10),transparent 28%),
      radial-gradient(circle at 88% 18%,rgba(15,159,143,.12),transparent 24%),
      var(--bg);color:var(--ink);}}
    header{{position:sticky;top:0;z-index:2;background:rgba(255,255,255,.92);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);}}
    .topbar{{max-width:1180px;margin:0 auto;padding:14px 22px;display:flex;align-items:center;justify-content:space-between;gap:18px;}}
    .brand{{display:flex;align-items:center;gap:10px;font-weight:800;}}
    .mark{{width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,var(--blue),var(--teal));display:grid;place-items:center;color:#fff;}}
    nav a{{color:#334155;text-decoration:none;font-weight:700;margin:0 8px;padding:8px 10px;border-radius:6px;}}
    nav a:hover{{background:#eef4ff;color:var(--blue);}}
    main{{max-width:1440px;margin:0 auto;padding:28px 22px 54px;}}
    h1{{font-size:30px;line-height:1.25;margin:0 0 8px;letter-spacing:0;}}
    h2{{font-size:20px;margin:0 0 10px;letter-spacing:0;}}
    h3{{font-size:16px;margin:0 0 8px;letter-spacing:0;}}
    p{{color:var(--muted);line-height:1.7;margin:0 0 10px;}}
    .hero{{display:grid;grid-template-columns:1.5fr .9fr;gap:18px;margin-bottom:18px;align-items:stretch;}}
    .assistant-hero h1{{font-size:38px;max-width:760px;}}
    .assistant-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}}
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
    .metrics{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:18px 0;opacity:.72;}}
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
    .article-workspace{{display:grid;grid-template-columns:240px minmax(0,1fr) 290px;gap:16px;align-items:start;}}
    .side-tools{{position:sticky;top:86px;display:flex;flex-direction:column;gap:12px;}}
    .preview{{background:#fff;padding:18px;border:1px solid var(--line);border-radius:8px;max-height:640px;overflow:auto;}}
    .final-preview-shell{{max-width:980px;margin:18px auto 0;}}
    .final-preview-shell .preview{{max-height:none;padding:22px;}}
    .final-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px;}}
    .blocks-workspace{{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start;}}
    .block-list{{display:grid;gap:12px;}}
    .block-card{{border:1px solid var(--line);border-radius:8px;background:#fff;padding:14px;box-shadow:0 10px 24px rgba(23,40,72,.06);}}
    .block-card[data-type="image"],.block-card[data-type="gallery"]{{background:#fbfdff;}}
    .block-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;}}
    .block-type{{font-size:12px;font-weight:900;color:#08735f;background:#dff8ef;border-radius:999px;padding:4px 8px;}}
    .block-tools{{display:flex;gap:6px;flex-wrap:wrap;}}
    .mini-btn{{min-height:28px;padding:5px 8px;margin:0;border-radius:6px;background:#eef4ff;color:var(--blue);font-size:12px;}}
    .mini-btn.danger{{background:#fff1f2;color:#be123c;}}
    .editable{{border:1px dashed transparent;border-radius:6px;padding:4px 6px;outline:none;}}
    .editable:focus{{border-color:#93c5fd;background:#f8fbff;}}
    .block-image{{width:100%;max-height:300px;object-fit:cover;border-radius:8px;border:1px solid var(--line);display:block;background:#eef3f8;}}
    .block-side{{position:sticky;top:86px;display:grid;gap:12px;}}
    .block-side .surface{{padding:16px;}}
    .block-json-label{{font-family:Consolas,monospace;font-size:12px;color:var(--muted);}}
    .draft-inline-status{{display:none;margin-top:14px;border-left:4px solid var(--teal);padding:12px 14px;background:#eefaf8;border-radius:6px;}}
    pre{{white-space:pre-wrap;background:#101827;color:#e2e8f0;padding:14px;border-radius:6px;overflow:auto;}}
    .score{{font-size:38px;font-weight:900;color:var(--teal);}}
    .asset-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}}
    .asset-card.is-hidden{{display:none!important;}}
    .empty-state{{display:none;border:1px dashed #b8c7dc;border-radius:8px;padding:18px;text-align:center;color:var(--muted);background:#fbfdff;}}
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
    .drawer{{display:none;position:fixed;right:22px;top:86px;width:min(640px,calc(100vw - 44px));max-height:calc(100vh - 112px);overflow:auto;background:rgba(255,255,255,.96);backdrop-filter:blur(18px);border:1px solid var(--line);border-radius:8px;padding:18px;box-shadow:0 24px 80px rgba(15,23,42,.22);z-index:5;}}
    .drawer:target{{display:block;animation:slideIn .2s ease both;}}
    .drawer-close{{float:right;}}
    .candidate{{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid #edf2f7;padding:10px 0;}}
    .candidate:last-child{{border-bottom:0;}}
    .style-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;}}
    .version-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}}
    .version-box{{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fbfdff;max-height:260px;overflow:auto;}}
    .image-slot-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}}
    .image-slot-card{{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fff;}}
    .selector-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px;}}
    .selector-item{{border:1px solid var(--line);border-radius:8px;padding:8px;background:#fbfdff;text-decoration:none;color:inherit;display:block;}}
    .selector-toolbar{{display:grid;grid-template-columns:1.2fr .8fr;gap:10px;margin:12px 0;}}
    .selector-actions{{display:flex;gap:6px;flex-wrap:wrap;}}
    .draft-steps{{display:grid;gap:8px;margin:10px 0;}}
    .draft-step{{border:1px solid var(--line);border-radius:6px;padding:8px 10px;color:var(--muted);background:#fbfdff;}}
    .draft-step.active{{border-color:#8fd8cc;background:#eefaf8;color:#08735f;}}
    .draft-step.done{{border-color:#a7d7b8;background:#effaf2;color:#187646;font-weight:800;}}
    .draft-error{{color:#b42318;font-weight:800;}}
    .draft-media{{font-family:Consolas,monospace;color:#1264d8;font-weight:900;word-break:break-all;}}
    .generator-strip{{position:relative;overflow:hidden;border:1px solid #bde7dd;background:rgba(239,250,248,.92);border-radius:8px;padding:12px 14px;margin:12px 0;color:#0f766e;font-weight:800;}}
    .generator-strip:after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent);transform:translateX(-100%);animation:scan 1.8s linear infinite;}}
    @keyframes scan{{to{{transform:translateX(100%)}}}}
    .template-drawer{{display:none;position:fixed;right:22px;top:86px;width:min(560px,calc(100vw - 44px));max-height:calc(100vh - 112px);overflow:auto;background:rgba(255,255,255,.96);backdrop-filter:blur(18px);border:1px solid var(--line);border-radius:8px;box-shadow:0 24px 80px rgba(15,23,42,.22);z-index:5;padding:18px;}}
    .template-drawer:target{{display:block;animation:slideIn .2s ease both;}}
    .full-wechat-preview{{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px;}}
    .full-wechat-preview .banner{{height:120px;border-radius:8px;background:linear-gradient(135deg,#dcecff,#e9fbf7);display:grid;place-items:center;color:#1264d8;font-weight:900;margin-bottom:12px;}}
    .asset-card,.option-card,.template-card,.article-card,.image-slot-card{{transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;}}
    .asset-card:hover,.option-card:hover,.template-card:hover,.article-card:hover,.image-slot-card:hover{{transform:translateY(-3px);box-shadow:0 18px 42px rgba(23,40,72,.12);border-color:#b8c7dc;}}
    .btn:hover,button:hover{{transform:translateY(-1px);filter:brightness(1.03);}}
    main{{animation:fadeIn .22s ease both;}}
    @keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
    .asset-drawer{{display:none;position:fixed;right:22px;top:86px;width:min(520px,calc(100vw - 44px));max-height:calc(100vh - 112px);overflow:auto;background:rgba(255,255,255,.94);backdrop-filter:blur(16px);border:1px solid var(--line);border-radius:8px;box-shadow:0 24px 80px rgba(15,23,42,.22);z-index:4;padding:18px;}}
    .asset-drawer:target{{display:block;animation:slideIn .2s ease both;}}
    @keyframes slideIn{{from{{opacity:0;transform:translateX(24px)}}to{{opacity:1;transform:none}}}}
    .pdf-card{{height:124px;border-radius:7px;background:linear-gradient(135deg,#fff7ed,#fee2e2);display:grid;place-items:center;margin-bottom:12px;color:#9f1239;font-weight:900;text-align:center;}}
    @media (max-width:1100px){{.article-workspace{{grid-template-columns:1fr}}.side-tools{{position:static}}}}
    @media (max-width:900px){{.hero,.preview-grid,.form-grid,.version-grid{{grid-template-columns:1fr}}.metrics,.cards,.asset-grid,.wizard,.option-grid,.style-grid,.image-slot-grid,.selector-grid,.workflow{{grid-template-columns:1fr}}}}
  </style>
  <script>
    function filterSelector(input, scopeId) {{
      var scope = document.getElementById(scopeId) || document;
      var keyword = (input.value || '').toLowerCase();
      var category = (scope.querySelector('[data-selector-category]') || {{value:''}}).value;
      scope.querySelectorAll('.selector-item').forEach(function(item) {{
        var name = (item.dataset.name || '').toLowerCase();
        var itemCategory = item.dataset.category || '';
        var hitText = !keyword || name.indexOf(keyword) >= 0;
        var hitCategory = !category || itemCategory === category;
        item.style.display = hitText && hitCategory ? 'block' : 'none';
      }});
    }}
    function filterSelectorCategory(select, scopeId) {{
      var scope = document.getElementById(scopeId) || document;
      var input = scope.querySelector('[data-selector-search]') || {{value:''}};
      filterSelector(input, scopeId);
    }}
    function filterAssets() {{
      var keyword = (document.getElementById('asset-search')?.value || '').toLowerCase();
      var category = document.getElementById('asset-category')?.value || '';
      var usage = document.getElementById('asset-usage')?.value || '';
      var visible = 0;
      document.querySelectorAll('[data-asset-card]').forEach(function(card) {{
        var name = (card.dataset.name || '').toLowerCase();
        var words = (card.dataset.keywords || '').toLowerCase();
        var itemCategory = card.dataset.category || '';
        var itemUsage = card.dataset.usage || '';
        var hitText = !keyword || name.indexOf(keyword) >= 0 || words.indexOf(keyword) >= 0;
        var hitCategory = !category || itemCategory === category;
        var hitUsage = !usage || itemUsage.indexOf(usage) >= 0;
        var show = hitText && hitCategory && hitUsage;
        card.classList.toggle('is-hidden', !show);
        if (show) visible += 1;
      }});
      var count = document.getElementById('asset-visible-count');
      if (count) count.textContent = visible;
      var empty = document.getElementById('asset-empty-state');
      if (empty) empty.style.display = visible ? 'none' : 'block';
    }}
    function publishDraft(articleId) {{
      var panel = document.getElementById('draft-result');
      var media = document.getElementById('draft-media-id');
      var message = document.getElementById('draft-message');
      var error = document.getElementById('draft-error');
      var steps = ['draft-step-token', 'draft-step-thumb', 'draft-step-create'];
      if (panel) panel.style.display = 'block';
      if (media) media.textContent = '';
      if (message) message.textContent = '';
      if (error) error.textContent = '';
      steps.forEach(function(id) {{
        var item = document.getElementById(id);
        if (item) item.className = 'draft-step active';
      }});
      fetch('/articles/' + articleId + '/publish-draft', {{method:'POST'}})
        .then(function(response) {{ return response.json().then(function(data) {{ return {{ok: response.ok, data: data}}; }}); }})
        .then(function(result) {{
          steps.forEach(function(id) {{
            var item = document.getElementById(id);
            if (item) item.className = 'draft-step done';
          }});
          if (!result.ok || !result.data.ok) throw new Error(result.data.error || '创建公众号草稿失败');
          if (media) media.textContent = result.data.media_id || '';
          if (message) message.textContent = result.data.message || '请登录微信公众号后台 → 内容与互动 → 草稿箱 查看';
        }})
        .catch(function(err) {{
          steps.forEach(function(id) {{
            var item = document.getElementById(id);
            if (item) item.className = 'draft-step';
          }});
          if (error) error.textContent = err.message;
        }});
    }}
    function moveBlock(button, direction) {{
      var card = button.closest('.block-card');
      var list = document.getElementById('block-list');
      if (!card || !list) return;
      if (direction < 0 && card.previousElementSibling) {{
        list.insertBefore(card, card.previousElementSibling);
      }}
      if (direction > 0 && card.nextElementSibling) {{
        list.insertBefore(card.nextElementSibling, card);
      }}
    }}
    function removeBlock(button) {{
      var card = button.closest('.block-card');
      if (card) card.remove();
    }}
    function collectBlocksFromDom() {{
      return Array.from(document.querySelectorAll('.block-card')).map(function(card) {{
        var block = JSON.parse(card.dataset.blockJson || '{{}}');
        card.querySelectorAll('[data-field]').forEach(function(field) {{
          var key = field.dataset.field;
          var value = field.value !== undefined ? field.value : field.textContent;
          if (key === 'items' || key === 'queries') {{
            block[key] = value.split('\\n').map(function(item) {{ return item.trim(); }}).filter(Boolean);
          }} else {{
            block[key] = value.trim();
          }}
        }});
        return block;
      }});
    }}
    function saveBlocks(articleId) {{
      var status = document.getElementById('blocks-save-status');
      if (status) status.textContent = '正在保存 blocks，并重新生成公众号 HTML...';
      fetch('/articles/' + articleId + '/save-blocks', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{blocks: collectBlocksFromDom()}})
      }})
      .then(function(response) {{ return response.json().then(function(data) {{ return {{ok: response.ok, data: data}}; }}); }})
      .then(function(result) {{
        if (!result.ok || !result.data.ok) throw new Error(result.data.error || '保存 blocks 失败');
        if (status) status.textContent = '已保存，正在刷新预览...';
        window.location.href = '/articles/' + articleId + '?saved=blocks';
      }})
      .catch(function(err) {{
        if (status) status.textContent = err.message;
      }});
    }}
  </script>
</head>
<body>
<header>
  <div class="topbar">
    <div class="brand"><div class="mark">AI</div><span>公众号内容 AI 员工</span></div>
    <nav>
      <a href="/">AI助手</a>
      <a href="/articles/new">新建文章</a>
      <a href="/assets">素材库</a>
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
    article_count = conn.execute("select count(*) from article_jobs").fetchone()[0]
    recent_cards = "".join(
        f"""
        <article class="article-card">
          <p class="muted">最近生成文章 · {escape(item['generation_mode_label'])}</p>
          <h3><a href="/articles/{item['id']}">{escape(item['title'])}</a></h3>
          <p>智能匹配结果已保存，可打开查看公众号预览或保存到草稿箱。</p>
          <a class="btn secondary" href="/articles/{item['id']}">打开预览</a>
        </article>
        """
        for item in articles[:6]
    ) or '<article class="article-card"><h3>还没有文章</h3><p>从开始创作进入，让 AI 员工生成第一篇公众号内容。</p></article>'
    body = f"""
<section class="assistant-hero">
  <div class="surface" style="text-align:center;padding:34px 28px;">
    <p class="muted">AI 助手入口</p>
    <h1>把素材、标题、配图和排版交给公众号内容 AI 助手</h1>
    <p>企业运营人员只需要输入基础信息，AI 助手会读取企业素材、生成文章、匹配配图，并整理成可复制或保存到微信公众号草稿箱的内容。</p>
    <div class="assistant-actions" style="justify-content:center;">
      <a class="btn" style="min-height:52px;font-size:18px;padding:14px 24px;" href="/articles/new">开始创作</a>
      <a class="btn secondary" href="/assets">查看素材分析</a>
    </div>
  </div>
</section>
<section class="metrics">
  <div class="metric"><span class="muted">素材数量</span><strong>{asset_count}</strong><p>已进入本地索引</p></div>
  <div class="metric"><span class="muted">文章生成数量</span><strong>{article_count}</strong><p>沉淀为历史记录</p></div>
</section>
<details class="surface">
  <summary><strong>最近生成文章（可折叠）</strong></summary>
  <div class="cards">{recent_cards}</div>
</details>"""
    return layout("AI 助手入口", body, api_key)


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
    <div class="generator-strip">AI助手正在准备：读取素材、匹配模板、规划标题和配图位置</div>
    <div class="recommend">生成中 AI 正在分析素材：产品图、参数图、品牌图会自动进入文章预览。</div>
    <button type="submit">生成文章</button>
  </section>
</form>"""
    return layout("新建文章", body, api_key)


def render_preview_page(conn, job_id: int) -> str:
    article = get_article(conn, job_id)
    latest = article["latest"]
    image_assets = [asset for asset in list_assets(conn, limit=10000) if asset["type"] == "image"]
    preview = (
        render_blocks_workspace(job_id, latest, image_assets)
        if latest.get("blocks")
        else f"<div class=\"preview\">{latest['html']}</div>"
    )
    body = f"""
<section class="surface">
    <p class="muted">文章预览 · 智能匹配结果</p>
    <h1>{escape(latest['title'])}</h1>
    <p>已生成可用于微信公众号后台的预览内容。确认无误后，可以复制 HTML，或直接保存到已配置的微信公众号草稿箱。</p>
    <div class="final-actions">
      <button onclick="navigator.clipboard && navigator.clipboard.writeText(document.getElementById('html-source').textContent)">复制HTML</button>
      <button type="button" class="btn teal" onclick="publishDraft({job_id})">保存到公众号草稿箱</button>
    </div>
    <div id="draft-result" class="draft-inline-status">
      <div class="draft-steps">
        <div id="draft-step-token" class="draft-step">获取公众号 access_token</div>
        <div id="draft-step-thumb" class="draft-step">上传封面图</div>
        <div id="draft-step-create" class="draft-step">创建草稿</div>
      </div>
      <p>草稿 media_id：<span id="draft-media-id" class="draft-media"></span></p>
      <p id="draft-message">请登录微信公众号后台 → 内容与互动 → 草稿箱 查看</p>
      <p id="draft-error" class="draft-error"></p>
    </div>
</section>
<section id="preview-content" class="surface final-preview-shell">
  <p class="muted">公众号正文预览优先</p>
  <h2>{'Blocks 可编辑预览' if latest.get('blocks') else '公众号样式预览'}</h2>
  {preview}
</section>
<pre id="html-source" hidden>{escape(latest['html'])}</pre>"""
    return layout("文章预览", body, "x" if latest["generation_mode"] == "api" else None)


def render_blocks_workspace(job_id: int, latest: dict, image_assets: list[dict]) -> str:
    image_slot_index = -1
    cards = []
    for idx, block in enumerate(latest.get("blocks") or []):
        if block.get("type") in {"image", "gallery"}:
            image_slot_index += 1
            slot = latest.get("image_slots", [])[image_slot_index] if image_slot_index < len(latest.get("image_slots", [])) else {}
        else:
            slot = {}
        cards.append(render_block_card(job_id, idx, block, slot, image_slot_index, image_assets))
    return f"""
<section class="blocks-workspace">
  <div id="block-list" class="block-list">{''.join(cards)}</div>
  <aside class="block-side">
    <section class="surface">
      <p class="muted">结构化内容</p>
      <h3>Blocks JSON 已启用</h3>
      <p>DeepSeek 返回 blocks，前端按 blocks 渲染。文字可直接编辑，图片按 query 匹配素材库。</p>
      <button type="button" class="btn teal" onclick="saveBlocks({job_id})">保存编辑</button>
      <p id="blocks-save-status" class="muted"></p>
    </section>
    <section class="surface">
      <p class="muted">操作说明</p>
      <p>上移、下移、删除会改变当前页面中的 blocks 顺序；保存后后端会重新转换微信公众号 HTML。</p>
    </section>
  </aside>
</section>"""


def render_block_card(
    job_id: int,
    idx: int,
    block: dict,
    slot: dict,
    slot_index: int,
    image_assets: list[dict],
) -> str:
    block_type = block.get("type", "paragraph")
    content = render_block_content(job_id, block, slot, slot_index, image_assets)
    block_json = escape(json.dumps(block, ensure_ascii=False))
    return f"""
<article class="block-card" data-type="{escape(block_type)}" data-block-json="{block_json}">
  <div class="block-head">
    <span class="block-type">{escape(block_type)}</span>
    <div class="block-tools">
      <button type="button" class="mini-btn" onclick="moveBlock(this,-1)">上移</button>
      <button type="button" class="mini-btn" onclick="moveBlock(this,1)">下移</button>
      <button type="button" class="mini-btn danger" onclick="removeBlock(this)">删除</button>
    </div>
  </div>
  {content}
</article>"""


def render_block_content(job_id: int, block: dict, slot: dict, slot_index: int, image_assets: list[dict]) -> str:
    block_type = block.get("type", "paragraph")
    if block_type == "heading":
        return f"<h2 class=\"editable\" contenteditable=\"true\" data-field=\"text\">{escape(block.get('text', ''))}</h2>"
    if block_type == "paragraph":
        return f"<p class=\"editable\" contenteditable=\"true\" data-field=\"text\">{escape(block.get('text', ''))}</p>"
    if block_type == "quote":
        return f"<blockquote class=\"editable\" contenteditable=\"true\" data-field=\"text\">{escape(block.get('text', ''))}</blockquote>"
    if block_type == "highlight":
        items = "\n".join(str(item) for item in block.get("items", []))
        return f"""
<h3 class="editable" contenteditable="true" data-field="title">{escape(block.get('title', '重点信息'))}</h3>
<label>重点条目<textarea data-field="items">{escape(items)}</textarea></label>"""
    if block_type == "image":
        return render_block_image(job_id, block, slot, slot_index, image_assets, gallery=False)
    if block_type == "gallery":
        queries = "\n".join(str(item) for item in block.get("queries", []))
        return render_block_image(job_id, block, slot, slot_index, image_assets, gallery=True) + f"""
<label>图库搜索 query<textarea data-field="queries">{escape(queries)}</textarea></label>"""
    if block_type == "cta":
        return f"""
<p class="editable" contenteditable="true" data-field="text">{escape(block.get('text', ''))}</p>
<p><strong>按钮：</strong><span class="editable" contenteditable="true" data-field="button_text">{escape(block.get('button_text', ''))}</span></p>"""
    if block_type == "divider":
        return '<section style="height:1px;background:#dbe3ef;margin:12px 0;"></section>'
    return f"<p class=\"editable\" contenteditable=\"true\" data-field=\"text\">{escape(block.get('text', ''))}</p>"


def render_block_image(job_id: int, block: dict, slot: dict, slot_index: int, image_assets: list[dict], gallery: bool) -> str:
    selected = slot.get("selected_asset_path") or slot.get("recommended_asset_path") or ""
    asset_id = slot.get("asset_id") or asset_id_for_path(image_assets, selected)
    if asset_id:
        image_html = f'<img class="block-image" alt="{escape(block.get("caption") or block.get("query") or "配图")}" src="/asset-thumb/{asset_id}">'
    else:
        image_html = '<div class="thumb" style="height:220px;">未匹配到图片，请从素材库替换</div>'
    query = block.get("query") or " / ".join(block.get("queries", []))
    caption = block.get("caption", "")
    choose = (
        f'<a class="btn secondary" href="/assets?article={job_id}&slot={slot_index}&return={quote(f"/articles/{job_id}#preview-content", safe="")}">从素材库换图</a>'
        if slot_index >= 0
        else ""
    )
    return f"""
{image_html}
<p class="block-json-label">query：{escape(query)}</p>
<p class="editable" contenteditable="true" data-field="caption">{escape(caption)}</p>
{choose}"""


def render_workflow() -> str:
    steps = ["创建", "生成", "标题优化", "AI改写", "图片调整", "最终确认", "复制HTML"]
    return '<section class="workflow">' + "".join(f'<span class="active">{step}</span>' for step in steps) + "</section>"


def render_draft_publish_panel(job_id: int) -> str:
    return f"""
<section class="recommend" style="margin-top:12px;">
  <h3>公众号草稿箱</h3>
  <p>只创建公众号草稿，不自动发布。未配置 AppID 或 AppSecret 时会使用 mock 模式跑完整流程。</p>
  <button type="button" onclick="publishDraft({job_id})">发布到公众号草稿箱</button>
  <div class="draft-steps">
    <div id="draft-step-token" class="draft-step">获取公众号 access_token</div>
    <div id="draft-step-thumb" class="draft-step">上传封面图</div>
    <div id="draft-step-create" class="draft-step">创建草稿</div>
  </div>
  <div id="draft-result" style="display:none;">
    <p>草稿 media_id：<span id="draft-media-id" class="draft-media"></span></p>
    <p id="draft-message">请登录微信公众号后台 → 内容与互动 → 草稿箱 查看</p>
    <p id="draft-error" class="draft-error"></p>
  </div>
  <p class="muted">接口：/articles/{job_id}/publish-draft</p>
</section>"""


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
    return f'<section id="title-drawer" class="drawer"><a href="#" class="btn secondary drawer-close">关闭</a><p class="muted">标题优化弹窗</p><h2>标题优化</h2><p>点击“采用”即可切换标题。</p>{rows}</section>'


def render_rewrite_drawer(job_id: int, original: dict, rewritten: dict | None) -> str:
    styles = ["更专业", "更营销", "更亲和", "更简洁", "更有科技感"]
    links = "".join(f'<a class="btn secondary" href="/articles/{job_id}/rewrite?style={quote(style)}">{style}</a>' for style in styles)
    rewritten_markdown = rewritten["markdown"] if rewritten else "尚未生成改写版本，请先选择一种改写风格。"
    return f"""
<section id="rewrite-drawer" class="drawer">
  <a href="#" class="btn secondary drawer-close">关闭</a>
  <p class="muted">AI改写弹窗</p>
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
        selector = "".join(render_selector_item(asset) for asset in image_assets)
    filters = render_selector_filters(image_assets, "image-drawer")
    return f"""
<section id="image-drawer" class="drawer">
  <a href="#" class="btn secondary drawer-close">关闭</a>
  <h2>图片调整</h2>
  <p>全部素材图片都在这里。生成文章后自动显示封面图、产品图、参数图、品牌图。案例图可在素材库选择器中继续补充。每个图片位都可以从素材库选择器中替换。</p>
  <div class="image-slot-grid">{slot_cards}</div>
  <h3 style="margin-top:16px;">素材库选择器</h3>
  {filters}
  <div class="selector-grid">{selector}</div>
</section>
{render_image_preview_drawers(image_assets)}"""


def render_image_slot_card(job_id: int, idx: int, slot: dict, image_assets: list[dict]) -> str:
    selected = slot.get("selected_asset_path") or slot.get("recommended_asset_path") or ""
    asset_id = asset_id_for_path(image_assets, selected)
    thumb = (
        f'<img alt="{escape(slot.get("position", "图片"))}" src="/asset-thumb/{asset_id}">'
        if asset_id
        else "<span>推荐素材列表</span>"
    )
    replacements = "".join(render_selector_item(asset, job_id, idx) for asset in image_assets)
    return f"""
<article class="image-slot-card">
  <h3>{escape(slot.get('position', f'图片位{idx + 1}'))}</h3>
  <div class="thumb">{thumb}</div>
  <p class="muted">当前推荐图片缩略图</p>
  <a class="btn secondary" href="#image-selector-{idx}">更换图片 · 打开图片选择器</a>
  <div id="image-selector-{idx}" style="margin-top:10px;">
    <h4>素材库选择器</h4>
    <div class="selector-grid">{replacements or '<p>推荐候选图片为空，请先补充素材。</p>'}</div>
  </div>
</article>"""


def render_used_image_list(slots: list[dict]) -> str:
    items = "".join(
        f"<li>{escape(slot.get('position', '图片'))}：{escape(Path(slot.get('selected_asset_path') or slot.get('recommended_asset_path') or '推荐候选图片').name)}</li>"
        for slot in slots
    )
    return f"<ul>{items}</ul>"


def render_selector_item(asset: dict, job_id: int | None = None, slot_idx: int = 0) -> str:
    choose_href = (
        f"/articles/{job_id}/replace-image?slot={slot_idx}&path={quote(asset['path'])}"
        if job_id is not None
        else "#"
    )
    name = Path(asset["path"]).name
    return f"""
<article class="selector-item" data-name="{escape(name)}" data-category="{escape(asset['category'])}">
  <a href="#image-preview-{asset['id']}" title="点击预览大图"><div class="thumb"><img alt="素材缩略图" src="/asset-thumb/{asset['id']}"></div></a>
  <p>{escape(name)}</p>
  <p class="muted">{escape(asset['category'])}</p>
  <div class="selector-actions">
    <a class="btn secondary" href="#image-preview-{asset['id']}">点击预览大图</a>
    <a class="btn" href="{choose_href}">选择替换当前图片</a>
  </div>
</article>"""


def render_selector_filters(image_assets: list[dict], scope_id: str) -> str:
    categories = sorted({asset["category"] for asset in image_assets})
    options = "".join(f'<option value="{escape(category)}">{escape(category)}</option>' for category in categories)
    return f"""
<div class="selector-toolbar">
  <label>搜索全部图片<input data-selector-search placeholder="搜索全部图片：产品、logo、海报" oninput="filterSelector(this, '{scope_id}')"></label>
  <label>图片分类筛选<select data-selector-category onchange="filterSelectorCategory(this, '{scope_id}')"><option value="">全部分类</option>{options}</select></label>
</div>"""


def render_image_preview_drawers(image_assets: list[dict]) -> str:
    return "".join(
        f"""
<aside id="image-preview-{asset['id']}" class="asset-drawer">
  <a href="#image-drawer" class="btn secondary" style="float:right;">返回选择器</a>
  <h2>点击预览大图</h2>
  <div class="thumb" style="height:360px;"><img alt="{escape(Path(asset['path']).name)}" src="/asset-thumb/{asset['id']}"></div>
  <p><strong>文件名</strong>：{escape(Path(asset['path']).name)}</p>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
</aside>"""
        for asset in image_assets
    )


def asset_id_for_path(image_assets: list[dict], path: str) -> int | None:
    for asset in image_assets:
        if asset["path"] == path:
            return int(asset["id"])
    return None


def render_asset_page(conn, article_id: int | None = None, slot_idx: int | None = None, return_to: str | None = None) -> str:
    assets = [asset for asset in list_assets(conn, limit=10000) if asset["type"] == "image"]
    return_to = return_to or (f"/articles/{article_id}" if article_id else "/assets")
    is_replacing = article_id is not None and slot_idx is not None
    cards = "".join(render_asset_card(asset, article_id, slot_idx, return_to) for asset in assets) or "<p>暂无素材，请先上传图片。</p>"
    drawers = "".join(render_asset_drawer(asset, article_id, slot_idx, return_to) for asset in assets)
    categories = sorted({asset["category"] for asset in assets})
    category_options = "".join(f"<option>{escape(category)}</option>" for category in categories)
    upload_query = ""
    if is_replacing:
        upload_query = f"?article={article_id}&slot={slot_idx}&return={quote(return_to, safe='')}"
    replace_notice = (
        f"""
<section class="surface recommend">
  <h2>正在为文章替换图片</h2>
  <p>你可以预览素材、上传新图，或选择任意图片替换当前图片位。替换完成后会自动回到文章预览。</p>
  <a class="btn secondary" href="{escape(return_to)}">不换了，返回文章预览</a>
</section>"""
        if is_replacing
        else ""
    )
    body = f"""
{replace_notice}
<section class="surface">
  <p class="muted">素材分析进度 · 素材卡片</p>
  <h1>素材库</h1>
  <p>这里只保留图片素材，PDF 和文档不在素材库中展示。点击图片放大预览，并可加入文章、作为封面或作为正文配图。</p>
</section>
<section class="surface">
  <h2>上传图片</h2>
  <form method="post" action="/assets/upload{upload_query}" enctype="multipart/form-data">
    <div class="form-grid">
      <label>选择图片<input type="file" name="asset_file" accept="image/*" multiple required></label>
      <label>上传说明<input name="note" placeholder="可选：产品图、活动海报、品牌logo"></label>
    </div>
    <p class="muted">支持一次选择多张图片批量上传。</p>
    <button type="submit">上传图片</button>
  </form>
</section>
<section class="surface">
  <h2>搜索与筛选</h2>
  <div class="form-grid">
    <label>搜索素材<input id="asset-search" placeholder="搜索素材：K2、直饮机、节日海报、logo" oninput="filterAssets()"></label>
    <label>分类筛选<select id="asset-category" onchange="filterAssets()"><option value="">全部分类</option>{category_options}</select></label>
    <label>用途筛选<select id="asset-usage" onchange="filterAssets()"><option value="">全部用途</option><option value="封面图">封面图</option><option value="正文配图">正文配图</option><option value="品牌区">品牌区</option></select></label>
  </div>
  <p class="recommend">当前显示 <strong id="asset-visible-count">{len(assets)}</strong> / {len(assets)} 个图片素材。搜索或筛选后会即时更新。</p>
</section>
<section class="asset-grid">{cards}</section>
<div id="asset-empty-state" class="empty-state">没有找到匹配素材，请调整搜索关键词或筛选条件。</div>
{drawers}"""
    return layout("素材库", body)


def render_asset_card(
    asset: dict,
    article_id: int | None = None,
    slot_idx: int | None = None,
    return_to: str = "/assets",
) -> str:
    name = Path(asset["path"]).name
    keywords = asset.get("keywords", [])[:4]
    chips = "".join(f"<span class='chip'>{escape(word)}</span>" for word in keywords) or "<span class='chip'>待分析</span>"
    thumb = asset_visual(asset, small=True)
    choose = ""
    if article_id is not None and slot_idx is not None:
        choose_href = replacement_href(article_id, slot_idx, asset["path"], return_to)
        choose = f'<a class="btn" href="{choose_href}">选择替换当前图片</a>'
    return f"""
<article class="asset-card" data-asset-card data-name="{escape(name)}" data-category="{escape(asset['category'])}" data-usage="{escape(recommended_use(asset))}" data-keywords="{escape(' '.join(asset.get('keywords', [])))}">
  <div class="thumb">{thumb}</div>
  <h3>{escape(name)}</h3>
  <p class="muted">点击图片放大预览</p>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
  <p><strong>关键词</strong>：{chips}</p>
  <p><strong>推荐用途</strong>：{escape(recommended_use(asset))}</p>
  <a class="btn secondary" href="#asset-{asset['id']}">点击预览大图</a>
  {choose}
</article>"""


def asset_visual(asset: dict, small: bool = False) -> str:
    if asset["type"] == "image":
        return f"<img alt='大图预览' src='/asset-thumb/{asset['id']}'>"
    if asset["type"] == "pdf":
        return "<div class='pdf-card'>PDF资料卡<br><span style='font-size:13px;color:#9f1239;'>第一页缩略图待生成</span></div>"
    return f"<span>{escape(asset['type'].upper())}</span>"


def render_asset_drawer(
    asset: dict,
    article_id: int | None = None,
    slot_idx: int | None = None,
    return_to: str = "/assets",
) -> str:
    name = Path(asset["path"]).name
    keywords = "".join(f"<span class='chip'>{escape(word)}</span>" for word in asset.get("keywords", [])[:8]) or "<span class='chip'>待分析</span>"
    page_count = asset.get("metadata", {}).get("pages") or "待解析"
    pdf_meta = f"<p><strong>页数</strong>：{page_count}</p>" if asset["type"] == "pdf" else ""
    choose = ""
    close_href = "#"
    if article_id is not None and slot_idx is not None:
        choose = f'<a class="btn" href="{replacement_href(article_id, slot_idx, asset["path"], return_to)}">选择替换当前图片</a>'
        close_href = "/assets?" + f"article={article_id}&slot={slot_idx}&return={quote(return_to, safe='')}"
    return f"""
<aside id="asset-{asset['id']}" class="asset-drawer">
  <a href="{close_href}" class="btn secondary" style="float:right;">关闭</a>
  <h2>素材详情</h2>
  <div class="thumb" style="height:220px;">{asset_visual(asset)}</div>
  <h3>大图预览</h3>
  <p><strong>文件名</strong>：{escape(name)}</p>
  <p><strong>文件类型</strong>：{escape(asset['type'])}</p>
  <p><strong>分类</strong>：{escape(asset['category'])}</p>
  {pdf_meta}
  <p><strong>关键词</strong>：{keywords}</p>
  <p><strong>推荐用途</strong>：{escape(recommended_use(asset))}</p>
  {choose or '<a class="btn" href="#">加入文章</a><a class="btn secondary" href="#">作为封面</a><a class="btn secondary" href="#">作为正文配图</a>'}
</aside>"""


def replacement_href(article_id: int, slot_idx: int, path: str, return_to: str) -> str:
    return (
        f"/articles/{article_id}/replace-image?slot={slot_idx}"
        f"&path={quote(path)}&return={quote(return_to, safe='')}"
    )


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
    drawers = "".join(render_template_drawer(row) for row in rows)
    return layout(
        "模板",
        f"<section class='surface'><p class='muted'>模板工作台</p><h1>模板</h1><p>每个模板都可以点击查看完整公众号预览，方便运营人员快速切换不同内容风格。</p></section><section class='cards'>{cards}</section>{drawers}",
    )


def render_template_card(row) -> str:
    outline = loads(row["outline"], [])
    outline_chips = "".join(f"<span class='chip'>{escape(item)}</span>" for item in outline[:4])
    return f"""
<a class="template-card" href="#template-{row['id']}" style="display:block;text-decoration:none;color:inherit;">
  <h2>{escape(row['name'])}</h2>
  <p>风格：{escape(row['style_name'])}</p>
  <p>{outline_chips}</p>
  <p class="muted">点击查看完整公众号预览</p>
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
</a>"""


def render_template_drawer(row) -> str:
    outline = loads(row["outline"], [])
    subtitle = escape(outline[1] if len(outline) > 1 else "核心卖点")
    cta = escape(row["cta_style"])
    return f"""
<aside id="template-{row['id']}" class="template-drawer">
  <a href="#" class="btn secondary drawer-close">关闭</a>
  <p class="muted">完整公众号预览</p>
  <h2>{escape(row['name'])}</h2>
  <div class="full-wechat-preview">
    <div class="banner">Banner图 · {escape(row['style_name'])}</div>
    <h1 style="font-size:24px;">企业饮水内容标题示例</h1>
    <p>正文段落：围绕企业真实运营场景，AI 会根据素材库提炼痛点、卖点和转化信息。</p>
    <h3>{subtitle}</h3>
    <blockquote style="margin:12px 0;padding:12px;border-left:4px solid #1264d8;background:#f4f8ff;">引用块：适合放置客户痛点、核心结论或品牌主张。</blockquote>
    <div class="thumb" style="height:150px;">图片区</div>
    <p>图文混排：产品图、参数图和品牌图会跟随模板风格实时呈现。</p>
    <div class="cta">{cta}</div>
  </div>
  <a class="btn" href="/articles/new">应用到当前文章</a>
</aside>"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        conn = self.server.conn
        try:
            if parsed.path == "/":
                self.respond(render_home_page(conn, self.server.api_key))
            elif parsed.path == "/runtime":
                self.respond_json(
                    {
                        "provider": get_model_provider(),
                        "model": get_model_name(),
                        "api_key_length": len(self.server.api_key or ""),
                        "label": model_runtime_label(self.server.api_key),
                    }
                )
            elif parsed.path == "/new":
                self.redirect("/articles/new")
            elif parsed.path == "/articles/new":
                self.respond(render_new_article_page(conn, self.server.api_key))
            elif parsed.path == "/assets":
                query = parse_qs(parsed.query)
                article_values = query.get("article", [])
                slot_values = query.get("slot", [])
                article_id = int(article_values[0]) if article_values and article_values[0].isdigit() else None
                slot_idx = int(slot_values[0]) if slot_values and slot_values[0].isdigit() else None
                return_to = query.get("return", [f"/articles/{article_id}" if article_id else "/assets"])[0]
                self.respond(render_asset_page(conn, article_id, slot_idx, return_to))
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
                self.redirect(query.get("return", [f"/articles/{job_id}"])[0])
            elif parsed.path.startswith("/articles/"):
                self.respond(render_preview_page(conn, int(parsed.path.split("/")[2])))
            else:
                self.send_error(404, "Not found")
        except Exception as exc:
            self.send_error(500, "Server error")

    def do_POST(self):
        parsed = urlparse(self.path)
        save_blocks_match = re.fullmatch(r"/articles/(\d+)/save-blocks", parsed.path)
        if save_blocks_match:
            job_id = int(save_blocks_match.group(1))
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                blocks = payload.get("blocks", [])
                if not isinstance(blocks, list):
                    raise ValueError("blocks 必须是数组")
                article = save_blocks(self.server.conn, job_id, blocks, self.server.api_key)
                self.respond_json({"ok": True, "version_id": article["version_id"]})
            except Exception as exc:
                self.respond_json({"ok": False, "error": f"保存 blocks 失败：{exc}"}, status=400)
            return
        draft_match = re.fullmatch(r"/articles/(\d+)/publish-draft", parsed.path)
        if draft_match:
            job_id = int(draft_match.group(1))
            try:
                result = WeChatDraftService(self.server.conn).publish_article_to_draft(job_id)
                self.respond_json(result)
            except WeChatDraftError as exc:
                self.respond_json({"ok": False, "error": str(exc), "response": exc.response}, status=400)
            except Exception as exc:
                self.respond_json({"ok": False, "error": f"创建公众号草稿失败：{exc}"}, status=500)
            return
        if parsed.path == "/assets/upload":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                uploads = parse_multipart_uploads(
                    self.rfile.read(length),
                    self.headers.get("Content-Type", ""),
                )
                for filename, data in uploads:
                    save_uploaded_image(self.server.conn, filename, data)
                self.redirect("/assets" + (f"?{parsed.query}" if parsed.query else ""))
            except ValueError:
                self.send_error(400, "Invalid image upload")
            return
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

    def respond_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
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
        mime = image_mime(suffix)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_asset_file(self, path: str):
        file_path = Path(path)
        if not path or not file_path.exists() or file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}:
            self.respond_svg_placeholder("image")
            return
        data = file_path.read_bytes()
        suffix = file_path.suffix.lower().lstrip(".") or "jpeg"
        mime = image_mime(suffix)
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
    load_local_env()
    conn = connect(db_path)
    init_db(conn)
    server = ThreadingHTTPServer((host, port), WorkbenchHandler)
    server.conn = conn
    server.api_key = get_api_key()
    print(f"微信公众号内容 AI 工作台已启动：http://localhost:{port}")
    print(f"当前生成模式：{model_runtime_label(server.api_key)}")
    server.serve_forever()


def parse_multipart_upload(body: bytes, content_type: str) -> tuple[str, bytes]:
    uploads = parse_multipart_uploads(body, content_type)
    return uploads[0]


def parse_multipart_uploads(body: bytes, content_type: str) -> list[tuple[str, bytes]]:
    match = re.search(r"boundary=([^;]+)", content_type)
    if not match:
        raise ValueError("missing boundary")
    boundary = match.group(1).strip('"').encode("utf-8")
    uploads = []
    for part in body.split(b"--" + boundary):
        if b'name="asset_file"' not in part or b"filename=" not in part:
            continue
        headers, _, content = part.partition(b"\r\n\r\n")
        filename_match = re.search(rb'filename="([^"]+)"', headers)
        if not filename_match:
            continue
        filename = filename_match.group(1).decode("utf-8", errors="ignore")
        cleaned = content.rstrip(b"\r\n-")
        if filename and cleaned:
            uploads.append((filename, cleaned))
    if not uploads:
        raise ValueError("missing asset_file")
    return uploads


def save_uploaded_image(conn, filename: str, data: bytes, upload_dir: str | Path | None = None) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in IMAGE_SUFFIXES or not data:
        raise ValueError("only image uploads are supported")
    safe_stem = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", Path(filename).stem).strip("_") or "uploaded"
    target_dir = Path(upload_dir or os.environ.get("WECHAT_AI_UPLOAD_DIR", Path(".tmp") / "uploads"))
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{safe_stem}{suffix}"
    counter = 1
    while target.exists():
        target = target_dir / f"{safe_stem}_{counter}{suffix}"
        counter += 1
    target.write_bytes(data)
    index_assets(conn, target_dir)
    return target


def image_mime(suffix: str) -> str:
    if suffix in {"jpg", "jpeg"}:
        return "image/jpeg"
    if suffix == "svg":
        return "image/svg+xml"
    return f"image/{suffix}"
