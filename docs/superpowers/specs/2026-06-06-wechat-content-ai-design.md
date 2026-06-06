# WeChat Official Account Content AI Design

## Background

Operations staff publish 3-5 WeChat Official Account articles each week. A single article can take 2-3 hours across topic framing, writing, image selection, and formatting. Existing paid editors reduce some formatting work, but still require manual operation and recurring membership costs.

This project builds a local AI content workstation for WeChat Official Account articles. The first version should help operations staff provide only basic article information, then automatically generate article copy, WeChat-compatible HTML, image placeholders, image recommendations, title options, rewrite variants, and quality scoring.

## Confirmed Product Direction

The selected direction is an automated content workstation, not a simple demo and not a fully autonomous publishing system.

The workstation includes both:

- A reusable command-line core for indexing assets and generating articles.
- A local web workstation for operations staff to create, preview, improve, and reuse articles.

The first version must work without external publishing permissions. It should keep a human review and manual publishing step by letting users copy generated HTML into the WeChat backend.

## In Scope For MVP

### Content Types

The MVP supports:

- New product launch articles.
- Holiday or campaign promotion articles.

The design should allow later templates for health education, installation cases, award announcements, and customer stories.

### Asset Processing

The system scans a configured local asset directory. The current reference asset directory is the `asset` folder under the user-provided WeChat content AI project folder on the desktop.

The MVP should parse:

- Markdown text.
- Word documents (`.docx`).
- PDF text where extractable.
- Images by filename, path, size, and inferred category.

PDFs that cannot yield text should remain indexed as file assets and be flagged as needing manual review.

### Article Generation

The system generates:

- Article title.
- Markdown body.
- WeChat-compatible HTML.
- SEO keywords.
- CTA.
- Image placeholders.
- Image recommendation list with local paths.
- Manual audit notes.
- Article quality score.

Generation supports two modes:

- Real model mode when a valid API key is configured.
- Simulation mode when no API key is configured, so the full workflow can run offline for demos and testing.

### Web Workstation

The local web workstation includes:

- Article task list and generation history.
- New article form.
- Template switching.
- Article preview page.
- One-click HTML copy.
- AI rewrite.
- Title optimization.
- Image replacement.
- Asset index status.
- Template list.

The first version does not need a complex rich-text editor. Users can review the preview, generate improved versions, copy HTML, and do final edits in the WeChat backend if needed.

### Templates

The MVP includes multiple templates:

- New product launch template.
- Holiday promotion template.
- Professional technology visual style.
- Campaign promotion visual style.
- Simple brand visual style.

Templates affect:

- Article outline.
- Title style.
- CTA style.
- HTML layout.
- Inline CSS styling.

### Article Quality Scoring

Each generated article version should receive a quality score.

The quality score includes:

- Overall score, 1-100.
- Title score.
- Structure score.
- Material usage score.
- Compliance score.
- Readability score.
- WeChat formatting score.
- Issues.
- Suggestions.

The MVP should support rule-based scoring. If a real model API is configured, it may also use AI scoring for richer suggestions.

### Search And Retrieval

The MVP uses SQLite with keyword search or SQLite FTS where practical.

Semantic search interfaces should be reserved from the start:

- `POST /api/search/assets`
- `POST /api/search/semantic`
- `POST /api/assets/embed`

For MVP, semantic search can fall back to keyword search. Production can later use PostgreSQL with pgvector, Elasticsearch, Milvus, or Qdrant.

### Storage

MVP storage uses SQLite for simple local deployment.

The data access layer should avoid hard-binding business logic to SQLite-only features. Production should be able to migrate to PostgreSQL, with future support for pgvector.

## Out Of Scope For MVP

The first version does not include:

- Automatic WeChat Official Account publishing.
- WeChat backend API integration.
- Automatic operation analytics.
- Automatic external hotspot collection.
- OSS or COS image upload.
- AI image generation.
- Scheduled publishing.
- A/B testing.

These are deferred because they depend on permissions, cloud credentials, platform APIs, or additional compliance review.

## Architecture

The system has five layers.

### 1. Asset Index Layer

Responsibilities:

- Scan configured asset folders.
- Parse Markdown, docx, and extractable PDF text.
- Record image files and metadata.
- Infer asset categories such as logo, product, poster, brochure, solution, or unknown.
- Extract keywords and text excerpts.
- Save index records locally.

### 2. Content Generation Core

Responsibilities:

- Accept normalized article input.
- Select a content template.
- Retrieve relevant material from the asset index.
- Generate or simulate article content.
- Produce Markdown, HTML, image slots, SEO keywords, CTA, and audit notes.
- Support rewrite and title optimization operations.

This core must be callable from both CLI and web APIs.

### 3. Layout Rendering Layer

Responsibilities:

- Convert Markdown into WeChat-compatible HTML.
- Apply inline CSS.
- Render headings, body text, quotes, dividers, CTA blocks, and image placeholders.
- Support multiple visual templates.
- Avoid base64 images to keep HTML size reasonable.

### 4. Local Workstation Layer

Responsibilities:

- Provide a local browser UI.
- Create article jobs.
- Display generation history.
- Preview article versions.
- Trigger rewrite, title optimization, and image replacement.
- Copy HTML to clipboard.
- Show quality score and audit notes.

### 5. Local Storage Layer

Responsibilities:

- Store asset index records.
- Store template definitions.
- Store article jobs.
- Store article versions.
- Store image replacement selections.
- Store quality scores.

MVP storage is SQLite. Production storage can migrate to PostgreSQL.

## Recommended Technology Stack

- Backend: Python FastAPI.
- CLI: Python Typer or argparse.
- Document parsing: `python-docx`, `pypdf`.
- Markdown rendering: `markdown` plus `BeautifulSoup` for post-processing.
- Image metadata: Pillow.
- Storage: SQLite for MVP, PostgreSQL for production.
- Frontend: simple local web UI. React/Vite is optional if interaction complexity grows.

## Data Model

### Asset

Fields:

- `id`
- `path`
- `type`: `image`, `markdown`, `docx`, `pdf`
- `category`: `logo`, `product`, `poster`, `brochure`, `solution`, `unknown`
- `text_excerpt`
- `keywords`
- `metadata`
- `created_at`
- `updated_at`

### Template

Fields:

- `id`
- `name`
- `content_type`
- `style_name`
- `outline`
- `html_style`
- `cta_style`
- `created_at`
- `updated_at`

### ArticleJob

Fields:

- `id`
- `content_type`
- `product_name`
- `occasion`
- `key_points`
- `target_audience`
- `tone`
- `image_requirement`
- `cta`
- `template_id`
- `status`
- `created_at`
- `updated_at`

### ArticleVersion

Fields:

- `id`
- `job_id`
- `title`
- `markdown`
- `html`
- `seo_keywords`
- `image_slots`
- `audit_notes`
- `version_type`: `initial`, `rewrite`, `title_optimized`, `image_replaced`
- `generation_mode`: `api`, `simulation`
- `created_at`

### ImageSlot

Fields:

- `id`
- `article_version_id`
- `position`
- `recommended_asset_path`
- `selected_asset_path`
- `alt_text`
- `placeholder_text`

### QualityScore

Fields:

- `id`
- `article_version_id`
- `overall_score`
- `title_score`
- `structure_score`
- `material_usage_score`
- `compliance_score`
- `readability_score`
- `wechat_format_score`
- `issues`
- `suggestions`
- `scoring_mode`: `rules`, `api`
- `created_at`

## API Design

### Asset APIs

- `POST /api/assets/reindex`: rescan the configured asset directory.
- `GET /api/assets`: list indexed assets.
- `POST /api/search/assets`: keyword search over assets.
- `POST /api/search/semantic`: reserved semantic search endpoint; MVP may fall back to keyword search.
- `POST /api/assets/embed`: reserved embedding endpoint; MVP may be a no-op or local cache operation.

### Template APIs

- `GET /api/templates`: list templates.
- `GET /api/templates/{id}`: get one template.

### Article APIs

- `POST /api/articles`: create and generate an article.
- `GET /api/articles`: list article history.
- `GET /api/articles/{id}`: get one article job with versions.
- `POST /api/articles/{id}/rewrite`: create a rewrite version.
- `POST /api/articles/{id}/optimize-title`: generate title candidates or a title-optimized version.
- `POST /api/articles/{id}/replace-image`: replace one image slot.
- `GET /api/articles/{id}/html`: get copy-ready HTML.
- `GET /api/articles/{id}/quality`: get article quality score.

## CLI Design

Example commands:

```bash
python -m wechat_ai reindex --asset-dir "<desktop wechat content ai project>/asset"
python -m wechat_ai generate --input examples/new_product.json
python -m wechat_ai preview --article-id 1
python -m wechat_ai score --article-id 1
```

The CLI should call the same application services as the web API.

## Core Workflow

1. User configures the local asset directory.
2. System scans and indexes assets.
3. User creates an article task in the web UI or via JSON input.
4. System selects or accepts a template.
5. System retrieves relevant product, campaign, or brand material.
6. System generates the article in API or simulation mode.
7. System renders WeChat-compatible HTML.
8. System recommends image slots and local image paths.
9. System scores article quality.
10. User previews the article.
11. User can optimize the title, rewrite the body, or replace image selections.
12. User copies HTML and publishes manually in the WeChat backend.
13. System saves all generated versions in history.

## Error Handling

- Missing matching assets: generate placeholders and add audit notes.
- Unreadable PDF text: index the file as an attachment and flag manual review.
- Missing API key: use simulation mode and mark the version accordingly.
- API failure: fall back to simulation mode and store the error internally.
- Article too short: add sections such as usage scenario, product advantage, or audit reminder.
- Absolute advertising terms in title: replace them or mark them for review.
- Oversized images: keep original file untouched and add a compression suggestion.
- HTML too large: avoid base64 images and keep styles inline but compact.

## Compliance And Security

- Do not write API keys into source code.
- Do not store API keys in article history.
- Use `.env` or local configuration for model keys.
- Do not upload customer or asset data externally unless the user explicitly configures a real model API.
- Do not invent customer cases. If no verified case is found in the asset library, add an audit note instead.
- Avoid absolute advertising terms such as "best", "first", and "top-level" in Chinese equivalents.
- Keep manual review before publication.

## Testing Plan

### Unit Tests

Cover:

- Asset scanner classification.
- Markdown/docx/PDF text extraction.
- Template selection.
- Markdown-to-HTML rendering.
- Image slot generation.
- Title compliance checks.
- Rule-based quality scoring.
- Simulation generation.

### Integration Tests

Cover:

- Reindex asset directory.
- Generate a new product article.
- Generate a holiday promotion article.
- Save and reload article history.
- Rewrite an article version.
- Optimize titles.
- Replace image slots.
- Retrieve copy-ready HTML.

### Manual Acceptance Tests

Use at least two fixed examples:

1. New product launch: 名士 K2 智能直饮机.
2. Holiday campaign: 618, 双 12, or 端午 promotion.

Generated results must include:

- Title.
- Markdown body.
- HTML.
- Image placeholders.
- Image recommendation list.
- SEO keywords.
- CTA.
- Audit notes.
- Quality score.

## Acceptance Criteria

The MVP is acceptable when:

- The asset library can be scanned and indexed.
- The web workstation can create and preview article jobs.
- The CLI can reindex assets and generate an article from JSON.
- New product and holiday promotion templates both work.
- Generated HTML uses inline styles and is copy-ready for WeChat backend review.
- One-click HTML copy works in the web UI.
- Title optimization creates multiple usable title candidates.
- AI rewrite creates a new article version.
- Image replacement updates the selected image slot and image list.
- Quality scoring returns scores, issues, and suggestions.
- No API key is required for the full workflow to run in simulation mode.
- The data model can be migrated from SQLite to PostgreSQL without redesigning business logic.

## Deferred Roadmap

Later versions can add:

- OSS or COS image upload.
- Public image URL generation.
- WeChat publishing API integration.
- Operation analytics.
- External hotspot collection.
- AI image generation.
- Automated weekly topic planning.
- Scheduled publishing.
- A/B title testing.
- PostgreSQL with pgvector.
- Full semantic retrieval over historical articles and assets.
