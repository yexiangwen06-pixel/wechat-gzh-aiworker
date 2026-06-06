# 微信公众号内容 AI 工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个最小可运行的中文本地 Web 工作台和 CLI，支持无 API Key 的模拟生成完整流程，并为真实模型、向量检索和 PostgreSQL 迁移预留接口。

**Architecture:** 使用 Python 标准库优先实现，避免 MVP 卡在依赖安装。核心服务位于 `wechat_ai/`，CLI 和 Web 页面复用同一套数据库、素材索引、生成、渲染和评分服务。

**Tech Stack:** Python 3、SQLite、unittest、标准库 `http.server`、`argparse`、`zipfile`、`sqlite3`。

---

## 文件结构

- Create: `wechat_ai/__init__.py`，包标识。
- Create: `wechat_ai/__main__.py`，CLI 入口。
- Create: `wechat_ai/config.py`，读取环境变量和默认路径。
- Create: `wechat_ai/db.py`，SQLite 连接、建表、模板初始化。
- Create: `wechat_ai/assets.py`，素材扫描、docx 文本抽取、关键词检索。
- Create: `wechat_ai/templates.py`，中文内置模板。
- Create: `wechat_ai/generator.py`，模拟生成和真实模型接口预留。
- Create: `wechat_ai/render.py`，Markdown 到公众号 HTML 的轻量渲染。
- Create: `wechat_ai/quality.py`，规则质量评分。
- Create: `wechat_ai/service.py`，文章任务、版本、改写、标题优化、图片替换的应用服务。
- Create: `wechat_ai/web.py`，本地 Web 工作台五个页面和 API-like 操作。
- Create: `examples/new_product.json`，新品上市输入样例。
- Create: `examples/holiday_campaign.json`，节日促销输入样例。
- Create: `tests/test_core.py`，核心流程单元测试。
- Create: `.gitignore`，忽略运行时数据库、缓存和临时视觉伴侣文件。
- Modify: `docs/superpowers/specs/2026-06-06-wechat-content-ai-design.md`，已补充中文文档、页面结构和模拟生成规则。

## Task 1: 项目骨架和数据库

**Files:**
- Create: `wechat_ai/__init__.py`
- Create: `wechat_ai/config.py`
- Create: `wechat_ai/db.py`
- Create: `wechat_ai/templates.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write failing database test**

Create `tests/test_core.py` with a test that creates a temporary database, initializes schema and templates, then asserts five core tables and two templates exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_core -v`
Expected: FAIL because `wechat_ai` modules do not exist.

- [ ] **Step 3: Implement minimal database and templates**

Create database helpers, schema creation, and Chinese built-in templates for `new_product` and `holiday_campaign`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_core -v`
Expected: PASS for database initialization.

## Task 2: 素材索引

**Files:**
- Modify: `tests/test_core.py`
- Create: `wechat_ai/assets.py`

- [ ] **Step 1: Write failing asset index test**

Add a test that creates temporary `.md`, `.docx`-like, `.pdf`, and image files, runs indexing, and asserts assets are stored with Chinese category labels and searchable keywords.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_core -v`
Expected: FAIL because `index_assets` is missing.

- [ ] **Step 3: Implement asset indexing**

Implement recursive scanning, file type detection, markdown text reading, simple docx XML extraction with `zipfile`, best-effort PDF text extraction, image metadata from file size and extension, and SQLite persistence.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_core -v`
Expected: PASS.

## Task 3: 模拟生成、渲染和质量评分

**Files:**
- Modify: `tests/test_core.py`
- Create: `wechat_ai/render.py`
- Create: `wechat_ai/quality.py`
- Create: `wechat_ai/generator.py`

- [ ] **Step 1: Write failing generation test**

Add a test that calls generation without API Key and asserts:
- `generation_mode == "simulation"`
- 页面展示文案应为 `模拟生成`
- 输出包含标题、Markdown、HTML、配图清单、审核要点和质量评分。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_core -v`
Expected: FAIL because generator modules are missing.

- [ ] **Step 3: Implement renderer, scorer, and simulation generator**

Implement simple Markdown rendering, compliance checks, rule score, title candidates, rewrite variants, and a real-model stub that only runs when API Key exists.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_core -v`
Expected: PASS.

## Task 4: 应用服务、CLI 和样例

**Files:**
- Modify: `tests/test_core.py`
- Create: `wechat_ai/service.py`
- Create: `wechat_ai/__main__.py`
- Create: `examples/new_product.json`
- Create: `examples/holiday_campaign.json`

- [ ] **Step 1: Write failing service and CLI tests**

Add tests for creating an article job, listing history, title optimization, rewrite, image replacement, and retrieving HTML.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_core -v`
Expected: FAIL because service functions are missing.

- [ ] **Step 3: Implement service and CLI**

Implement `reindex`, `generate`, `list`, `score`, and `serve` commands. Persist article jobs, versions, image slots, and quality scores.

- [ ] **Step 4: Run unit tests and smoke CLI**

Run:
- `python -m unittest tests.test_core -v`
- `python -m wechat_ai generate --input examples/new_product.json --db .tmp/demo.db`
Expected: tests PASS and CLI prints article id, generation mode, and preview path hint.

## Task 5: 中文本地 Web 工作台

**Files:**
- Modify: `tests/test_core.py`
- Create: `wechat_ai/web.py`

- [ ] **Step 1: Write failing web rendering tests**

Add tests that render the five page HTML functions and assert Chinese page titles:
- 首页
- 新建文章
- 文章预览
- 素材库
- 模板

Also assert no API Key state displays `模拟生成`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_core -v`
Expected: FAIL because web functions are missing.

- [ ] **Step 3: Implement web pages**

Implement local HTTP server with routes:
- `/`
- `/articles/new`
- `/articles/create`
- `/articles/{id}`
- `/assets`
- `/templates`
- `/articles/{id}/optimize-title`
- `/articles/{id}/rewrite`
- `/articles/{id}/replace-image`
- `/articles/{id}/html`

All visible copy must be Chinese. Preview page must clearly show `模拟生成` or `真实模型生成`.

- [ ] **Step 4: Run tests and start demo server**

Run:
- `python -m unittest tests.test_core -v`
- `python -m wechat_ai serve --db .tmp/demo.db --port 8765`
Expected: tests PASS and local URL `http://localhost:8765` starts.

## Task 6: 验证和整理

**Files:**
- Create: `.gitignore`
- Modify: any files needing cleanup.

- [ ] **Step 1: Ignore runtime files**

Ignore:
- `.tmp/`
- `__pycache__/`
- `.superpowers/`
- `visual-preview.html`

- [ ] **Step 2: Run final verification**

Run:
- `python -m unittest tests.test_core -v`
- `python -m wechat_ai generate --input examples/new_product.json --db .tmp/final.db`

Expected:
- all tests pass.
- CLI output marks `模拟生成`.
- generated article includes HTML.

- [ ] **Step 3: Commit**

Commit the Chinese spec update and MVP demo implementation.
