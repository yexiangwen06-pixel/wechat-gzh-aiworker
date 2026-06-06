# 微信公众号内容生成与排版 AI 员工设计规格

## 1. 项目背景

运营人员每周需要发布 3-5 篇微信公众号文章。一篇文章从选题、撰写、配图到排版通常需要 2-3 小时。现有编辑器能减少部分排版工作，但仍需要人工操作，并存在会员成本。

本项目要构建一个本地 Web 内容工作台。运营人员只输入基础信息，系统自动读取素材库，生成公众号文章、标题候选、Markdown 正文、公众号 HTML、配图占位、配图清单、审核要点和文章质量评分。

## 2. 产品定位

第一版选择“自动化内容工作台”方向，而不是简单脚本，也不是全自动发布系统。

系统包含两个入口：

- 命令行核心：用于素材索引、文章生成、质量评分，方便测试和自动化调用。
- 本地 Web 工作台：用于企业导师、答辩和运营人员演示，包括页面填写、文章预览、一键复制 HTML、AI 改写、标题优化和图片替换。

第一版保留人工审核与人工发布环节。系统生成可复制 HTML，用户再粘贴到微信公众号后台发布。

## 3. MVP 范围

### 3.1 内容类型

第一版支持：

- 新品上市。
- 节日促销。

后续可以扩展：

- 健康科普。
- 装机案例。
- 获奖推送。
- 客户故事。

### 3.2 素材处理

系统扫描用户配置的本地素材目录。当前参考目录是桌面项目文件夹下的 `asset` 文件夹。

MVP 需要解析：

- Markdown 文本。
- Word 文档（`.docx`）。
- 可抽取文字的 PDF。
- 图片文件名、路径、尺寸、大小和推断分类。

如果 PDF 无法抽取文字，系统仍然把它作为素材附件记录，并在审核要点里提示人工确认。

### 3.3 内容生成

系统输出：

- 文章标题。
- Markdown 正文。
- 微信公众号兼容 HTML。
- SEO 关键词。
- CTA 行动召唤。
- 图片占位。
- 推荐配图清单和本地路径。
- 人工审核要点。
- 文章质量评分。

生成模式分为两种：

- 真实模型模式：只有配置 API Key 时才调用真实大模型。
- 模拟生成模式：没有 API Key 时自动启用，用模板和素材摘要跑通完整流程。

页面上必须清楚标记当前文章是“模拟生成”还是“真实模型生成”。

### 3.4 Web 工作台功能

本地 Web 工作台需要包含：

- 多模板切换。
- 文章预览页面。
- 一键复制 HTML。
- AI 改写。
- 标题优化。
- 图片替换。
- 生成历史。
- 素材库索引状态。
- 文章质量评分。

第一版不做复杂富文本编辑器。用户可以在系统中生成和优化，再复制 HTML 到微信公众号后台做最终发布。

### 3.5 模板

MVP 内置：

- 新品上市模板。
- 节日促销模板。
- 专业科技风。
- 促销活动风。
- 简洁品牌风。

模板影响：

- 文章结构。
- 标题风格。
- CTA 样式。
- HTML 排版。
- 内联 CSS。

### 3.6 文章质量评分

每个文章版本都要生成质量评分：

- 总分：1-100。
- 标题吸引力。
- 结构完整度。
- 素材引用充分度。
- 合规风险。
- 可读性。
- 公众号排版适配度。
- 问题列表。
- 优化建议。

MVP 使用规则评分。有 API Key 时可以追加 AI 评分建议。

### 3.7 检索与向量接口预留

MVP 使用 SQLite 和关键词检索，也可以使用 SQLite FTS。

从接口层预留语义检索能力：

- `POST /api/search/assets`：素材关键词检索。
- `POST /api/search/semantic`：语义检索预留，MVP 可回退到关键词检索。
- `POST /api/assets/embed`：素材向量生成预留，MVP 可为空实现或本地缓存。

生产环境可以迁移到：

- PostgreSQL + pgvector。
- Elasticsearch。
- Milvus。
- Qdrant。

### 3.8 数据库

MVP 使用 SQLite：

- 部署简单。
- 适合本地单机演示。
- 方便快速开发和答辩展示。

生产环境可迁移 PostgreSQL：

- 数据访问层隔离数据库实现。
- JSON 字段、时间字段、外键关系按可迁移方式设计。
- 后续可接 pgvector 做语义检索。

## 4. MVP 不做的内容

第一版暂不做：

- 自动发布微信公众号。
- 微信公众号后台接口对接。
- 自动运营数据分析。
- 自动搜集热点。
- OSS / COS 图床自动上传。
- AI 生图。
- 定时发布。
- A/B 测试。

原因是这些能力依赖外部账号、平台权限、云密钥或更多合规验证。

## 5. 本地 Web 工作台页面结构

### 5.1 首页

用途：展示系统状态和生成历史。

核心内容：

- 当前生成模式：模拟生成 / 真实模型生成。
- 素材库索引状态。
- 最近生成文章列表。
- 新建文章入口。
- 快速重新索引按钮。

### 5.2 新建文章页

用途：填写基础信息并创建文章任务。

表单字段：

- 内容类型：新品上市 / 节日促销。
- 模板风格。
- 产品名或活动名。
- 核心卖点或促销信息。
- 目标人群。
- 语气。
- 配图要求。
- CTA。

提交后系统生成文章初稿并跳转到文章预览页。

### 5.3 文章预览页

用途：查看生成结果并做轻量优化。

页面模块：

- 当前生成模式标记。
- 文章质量评分。
- 标题区和标题候选。
- 公众号样式预览。
- Markdown 正文。
- HTML 源码。
- 配图清单。
- 审核要点。

操作按钮：

- 一键复制 HTML。
- 标题优化。
- AI 改写。
- 图片替换。

### 5.4 素材库页

用途：查看系统扫描到的素材。

页面模块：

- 素材数量统计。
- 图片 / 文档 / PDF 分类。
- 素材搜索。
- 素材路径。
- 文本摘要。
- 重新索引入口。

### 5.5 模板页

用途：查看可用模板和风格。

页面模块：

- 模板列表。
- 内容类型。
- 文章结构说明。
- 排版风格说明。
- CTA 样式说明。

MVP 先支持查看模板，后续再做模板编辑。

## 6. 系统架构

系统分为五层。

### 6.1 素材索引层

负责：

- 扫描素材目录。
- 解析 Markdown、docx、PDF。
- 读取图片元数据。
- 推断素材分类。
- 提取关键词和文本摘要。
- 保存素材索引。

### 6.2 内容生成核心层

负责：

- 接收标准化文章输入。
- 选择模板。
- 检索相关素材。
- 真实模型生成或模拟生成。
- 输出 Markdown、HTML、SEO 关键词、CTA、图片占位和审核要点。
- 支持 AI 改写和标题优化。

命令行和 Web API 都调用这一层。

### 6.3 排版渲染层

负责：

- Markdown 转微信公众号 HTML。
- 应用内联 CSS。
- 渲染标题、正文、引用、分割线、CTA 和图片占位。
- 支持多种视觉模板。
- 不使用 base64 图片，避免 HTML 体积过大。

### 6.4 本地工作台层

负责：

- 提供中文页面。
- 创建文章任务。
- 展示生成历史。
- 展示文章预览。
- 触发改写、标题优化和图片替换。
- 一键复制 HTML。
- 展示质量评分和审核要点。

### 6.5 本地存储层

负责保存：

- 素材索引。
- 模板配置。
- 文章任务。
- 文章版本。
- 图片替换记录。
- 质量评分。

## 7. 技术栈

推荐技术栈：

- 后端：Python。
- Web Demo：Python 标准库 HTTP 服务或 FastAPI。
- CLI：Python argparse 或 Typer。
- 文档解析：标准库能力优先，后续可接 `python-docx`、`pypdf`。
- Markdown 渲染：MVP 可用内部轻量渲染器，后续可接 `markdown` 和 `BeautifulSoup`。
- 图片元数据：MVP 记录文件大小和扩展名，后续可接 Pillow。
- 数据库：SQLite，生产迁移 PostgreSQL。

## 8. 数据模型

### 8.1 Asset 素材

- `id`
- `path`
- `type`
- `category`
- `text_excerpt`
- `keywords`
- `metadata`
- `created_at`
- `updated_at`

### 8.2 Template 模板

- `id`
- `name`
- `content_type`
- `style_name`
- `outline`
- `html_style`
- `cta_style`
- `created_at`
- `updated_at`

### 8.3 ArticleJob 文章任务

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

### 8.4 ArticleVersion 文章版本

- `id`
- `job_id`
- `title`
- `markdown`
- `html`
- `seo_keywords`
- `image_slots`
- `audit_notes`
- `version_type`
- `generation_mode`
- `created_at`

### 8.5 ImageSlot 图片占位

- `id`
- `article_version_id`
- `position`
- `recommended_asset_path`
- `selected_asset_path`
- `alt_text`
- `placeholder_text`

### 8.6 QualityScore 质量评分

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
- `scoring_mode`
- `created_at`

## 9. API 设计

### 9.1 素材接口

- `POST /api/assets/reindex`
- `GET /api/assets`
- `POST /api/search/assets`
- `POST /api/search/semantic`
- `POST /api/assets/embed`

### 9.2 模板接口

- `GET /api/templates`
- `GET /api/templates/{id}`

### 9.3 文章接口

- `POST /api/articles`
- `GET /api/articles`
- `GET /api/articles/{id}`
- `POST /api/articles/{id}/rewrite`
- `POST /api/articles/{id}/optimize-title`
- `POST /api/articles/{id}/replace-image`
- `GET /api/articles/{id}/html`
- `GET /api/articles/{id}/quality`

## 10. CLI 设计

示例命令：

```bash
python -m wechat_ai reindex --asset-dir "<desktop wechat content ai project>/asset"
python -m wechat_ai generate --input examples/new_product.json
python -m wechat_ai preview --article-id 1
python -m wechat_ai score --article-id 1
python -m wechat_ai serve
```

CLI 和 Web API 复用同一套核心服务。

## 11. 核心流程

1. 用户配置本地素材目录。
2. 系统扫描并索引素材。
3. 用户通过网页表单或 JSON 创建文章任务。
4. 系统选择模板。
5. 系统检索相关产品、活动或品牌素材。
6. 系统判断生成模式：无 API Key 使用模拟生成，有 API Key 才调用真实模型。
7. 系统生成文章正文、标题、HTML、配图清单和审核要点。
8. 系统生成文章质量评分。
9. 用户在预览页查看文章。
10. 用户可进行标题优化、AI 改写、图片替换。
11. 用户一键复制 HTML。
12. 用户到微信公众号后台人工预览并发布。
13. 系统保存生成历史和版本。

## 12. 异常处理

- 找不到匹配素材：生成图片或资料占位，并加入审核要点。
- PDF 无法抽取文字：记录文件路径，并提示人工审核。
- 没有 API Key：启用模拟生成，并在页面明显标记“模拟生成”。
- API 调用失败：回退模拟生成，并记录错误信息。
- 文章过短：自动补充场景痛点、产品优势或审核提示。
- 标题包含广告法高风险词：自动替换或提示审核。
- 图片过大：不改原图，只在配图清单里提示压缩。
- HTML 体积过大：不嵌入 base64 图片，仅保留占位和路径。

## 13. 安全与合规

- API Key 不写入源码。
- API Key 不进入文章历史。
- 未显式配置真实模型时，不把素材上传到外部服务。
- 不编造客户案例。
- 找不到真实案例时写入审核提示。
- 标题避免“最好、第一、顶级”等绝对化表达。
- 发布前保留人工审核。

## 14. 测试计划

单元测试覆盖：

- 数据库建表。
- 模板初始化。
- 素材扫描分类。
- 模拟生成完整输出。
- Markdown 转 HTML。
- 标题合规检查。
- 质量评分。
- 无 API Key 时生成模式标记。

集成测试覆盖：

- 重新索引素材。
- 生成新品上市文章。
- 生成节日促销文章。
- 保存和读取生成历史。
- 标题优化。
- AI 改写。
- 图片替换。
- 获取可复制 HTML。

## 15. 验收标准

MVP 达到以下标准即可验收：

- 文档和页面文案均为中文，便于导师和答辩展示。
- 首页、新建文章页、文章预览页、素材库页、模板页均可访问。
- 无 API Key 时完整流程可运行，并显示“模拟生成”。
- 有 API Key 时才进入真实模型调用路径。
- CLI 可以索引素材并从 JSON 生成文章。
- Web 工作台可以创建文章并进入预览页。
- 新品上市和节日促销模板都能生成。
- 生成结果包含标题、Markdown、HTML、配图清单、审核要点和质量评分。
- 一键复制 HTML 按钮存在且可复制预览 HTML。
- 标题优化、AI 改写、图片替换能生成或更新文章版本。
- SQLite 中保存素材、模板、文章、版本和评分数据。
- 数据访问层保留 PostgreSQL 迁移空间。

## 16. 后续路线

后续版本可以增加：

- OSS / COS 图床上传。
- 公网图片 URL。
- 微信公众号发布接口。
- 运营数据分析。
- 外部热点搜集。
- AI 生图。
- 每周自动选题。
- 定时发布。
- 标题 A/B 测试。
- PostgreSQL + pgvector。
- 历史文章和素材的完整语义检索。
