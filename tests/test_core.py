import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


class WechatAiCoreTests(unittest.TestCase):
    def make_db(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "test.db"

    def make_asset_dir(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "素材说明.md").write_text("# 名士K2\n2000G大流量\nDPM动态蛋白纳滤", encoding="utf-8")
        (root / "端午促销海报.jpg").write_bytes(b"fake image")
        (root / "K2产品图.jpg").write_bytes(b"fake product image")
        (root / "朴道logo.png").write_bytes(b"fake logo image")
        (root / "K2产品单页.pdf").write_bytes(b"%PDF Pudow K2 2000G IoT")
        docx_path = root / "素材.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr(
                "word/document.xml",
                "<w:document><w:body><w:p><w:r><w:t>企业饮水解决方案</w:t></w:r></w:p></w:body></w:document>",
            )
        return root

    def setup_app(self):
        from wechat_ai.assets import index_assets
        from wechat_ai.db import connect, init_db

        conn = connect(self.make_db())
        init_db(conn)
        index_assets(conn, self.make_asset_dir())
        return conn

    def test_database_initializes_core_tables_and_templates(self):
        from wechat_ai.db import connect, init_db

        conn = connect(self.make_db())
        init_db(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
        }
        self.assertTrue(
            {
                "assets",
                "templates",
                "article_jobs",
                "article_versions",
                "image_slots",
                "quality_scores",
            }.issubset(tables)
        )
        templates = [tuple(row) for row in conn.execute("select name from templates order by id").fetchall()]
        self.assertIn(("新品上市模板",), templates)
        self.assertIn(("节日促销模板",), templates)

    def test_asset_indexing_stores_documents_images_and_searches_keywords(self):
        from wechat_ai.assets import search_assets

        conn = self.setup_app()
        image = conn.execute("select category from assets where path like '%海报.jpg'").fetchone()
        self.assertEqual(image[0], "海报")
        hits = search_assets(conn, "K2")
        self.assertTrue(any("K2" in hit["text_excerpt"] or "K2" in hit["path"] for hit in hits))

    def test_simulation_generation_returns_complete_article_and_quality_score(self):
        from wechat_ai.service import create_article

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量", "DPM动态蛋白纳滤", "IoT智能管理"],
                "target_audience": "企业采购决策者",
                "tone": "专业、科技感",
                "image_requirement": "产品图3张",
                "cta": "预约企业饮水方案咨询",
                "template_id": 1,
            },
            api_key=None,
        )
        self.assertEqual(article["generation_mode"], "simulation")
        self.assertEqual(article["generation_mode_label"], "模拟生成")
        self.assertIn("名士K2", article["title"])
        self.assertIn("<section", article["html"])
        self.assertIn("<img", article["html"])
        self.assertIn("Banner图", article["html"])
        self.assertIn("CTA按钮", article["html"])
        self.assertGreaterEqual(len(article["image_slots"]), 1)
        self.assertGreaterEqual(article["quality_score"]["overall_score"], 60)

    def test_config_loads_local_env_file_as_desktop_source_of_truth(self):
        from wechat_ai.config import load_local_env

        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        env_file = Path(tmp.name) / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "WECHAT_APP_ID=wx-from-file",
                    "WECHAT_APP_SECRET=\"secret from file\"",
                    "WECHAT_DRAFT_MODE=real",
                    "DEEPSEEK_API_KEY=deepseek-from-file",
                    "WECHAT_AI_PROVIDER=deepseek",
                    "IGNORED_LINE",
                    "# comment",
                ]
            ),
            encoding="utf-8",
        )
        env = {"WECHAT_APP_ID": "wx-existing"}

        loaded = load_local_env(env_file, env)

        self.assertTrue(loaded)
        self.assertEqual(env["WECHAT_APP_ID"], "wx-from-file")
        self.assertEqual(env["WECHAT_APP_SECRET"], "secret from file")
        self.assertEqual(env["WECHAT_DRAFT_MODE"], "real")
        self.assertEqual(env["DEEPSEEK_API_KEY"], "deepseek-from-file")
        self.assertEqual(env["WECHAT_AI_PROVIDER"], "deepseek")
        self.assertNotIn("IGNORED_LINE", env)

    def test_vercel_configuration_routes_all_paths_to_python_entry(self):
        config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))

        self.assertTrue(Path("api/index.py").exists())
        self.assertTrue(Path("requirements.txt").exists())
        self.assertEqual(
            config["rewrites"],
            [{"source": "/(.*)", "destination": "/api/index.py"}],
        )
        self.assertNotIn("functions", config)

    def test_vercel_entry_initializes_tmp_sqlite_and_env_runtime(self):
        from types import SimpleNamespace
        import api.index as vercel_entry

        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        db_path = str(Path(tmp.name) / "vercel.db")
        upload_dir = str(Path(tmp.name) / "uploads")
        env = {
            "VERCEL": "1",
            "WECHAT_AI_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "deepseek-test-key",
            "DEEPSEEK_MODEL": "deepseek-v4-flash",
            "WECHAT_AI_VERCEL_DB": db_path,
            "WECHAT_AI_UPLOAD_DIR": upload_dir,
        }
        with patch.dict(os.environ, env, clear=False):
            vercel_entry._CONN = None
            server = SimpleNamespace()
            vercel_entry.configure_server(server)

        tables = {
            row[0]
            for row in server.conn.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
        }
        asset_count = server.conn.execute("select count(*) from assets").fetchone()[0]
        self.assertIn("article_jobs", tables)
        self.assertEqual(server.api_key, "deepseek-test-key")
        self.assertTrue(Path(db_path).exists())
        self.assertGreaterEqual(asset_count, 5)

    def test_api_generation_uses_model_output_and_keeps_wechat_preview_images(self):
        from wechat_ai.service import create_article

        conn = self.setup_app()
        captured = {}

        def fake_openai_call(api_key, model, payload, assets, rewrite_hint=None):
            captured["api_key"] = api_key
            captured["model"] = model
            captured["payload"] = payload
            captured["assets"] = assets
            return {
                "title": "真实模型生成标题：K2企业饮水解决方案",
                "markdown": "## 真实模型正文\n\n这是一段由真实模型接口生成的公众号文章预览正文。\n\n### 行动召唤\n预约企业饮水方案。",
                "seo_keywords": ["K2", "企业饮水", "公众号文章"],
                "audit_notes": ["真实模型已生成，请核对参数。"],
            }

        with patch("wechat_ai.generator.call_openai_article_api", side_effect=fake_openai_call):
            article = create_article(
                conn,
                {
                    "content_type": "new_product",
                    "product_name": "名士K2智能直饮机",
                    "key_points": ["2000G大流量", "IoT智能管理"],
                    "target_audience": "企业采购决策者",
                    "tone": "专业、科技感",
                    "image_requirement": "封面图+产品图",
                    "cta": "预约企业饮水方案",
                    "template_id": 1,
                },
                api_key="sk-test",
            )

        self.assertEqual(article["generation_mode"], "api")
        self.assertEqual(article["generation_mode_label"], "真实模型生成")
        self.assertEqual(article["title"], "真实模型生成标题：K2企业饮水解决方案")
        self.assertIn("真实模型接口生成", article["markdown"])
        self.assertIn("真实模型正文", article["html"])
        self.assertIn("<img", article["html"])
        self.assertGreaterEqual(len(article["image_slots"]), 1)
        self.assertEqual(captured["api_key"], "sk-test")
        self.assertTrue(captured["model"])
        self.assertTrue(any(asset["type"] == "image" for asset in captured["assets"]))

    def test_deepseek_generation_uses_deepseek_provider_and_chat_completion_shape(self):
        from wechat_ai.service import create_article
        from wechat_ai.web import render_asset_page, render_preview_page

        conn = self.setup_app()
        captured = {}

        def fake_deepseek_call(api_key, model, payload, assets, rewrite_hint=None):
            captured["api_key"] = api_key
            captured["model"] = model
            captured["payload"] = payload
            captured["assets"] = assets
            return {
                "title": "DeepSeek blocks 标题：企业饮水内容预览",
                "title_options": [
                    "名士K2智能直饮机：企业饮水效率升级",
                    "企业茶水间需要怎样的智能直饮方案",
                    "从饮水体验看办公室效率升级",
                    "名士K2如何服务企业饮水场景",
                    "企业饮水方案，不只是一台直饮机",
                ],
                "digest": "围绕名士K2智能直饮机，生成适合公众号预览和后续编辑的结构化内容。",
                "cover": {
                    "query": "名士K2智能直饮机 企业办公饮水场景",
                    "image_generation_prompt": "企业办公茶水间中的智能直饮机产品图",
                },
                "blocks": [
                    {"type": "heading", "level": 2, "text": "从企业饮水效率切入"},
                    {"type": "paragraph", "text": "这是一段由 DeepSeek blocks JSON 生成的公众号文章正文。"},
                    {"type": "quote", "text": "好的饮水方案，应当同时照顾员工体验和运营效率。"},
                    {
                        "type": "image",
                        "query": "名士K2智能直饮机 产品外观",
                        "caption": "产品外观",
                        "image_generation_prompt": "白色智能直饮机产品外观特写",
                    },
                    {
                        "type": "highlight",
                        "title": "企业运营关注的三点",
                        "items": ["稳定供水", "智能管理", "健康体验"],
                    },
                    {
                        "type": "gallery",
                        "queries": ["企业茶水间饮水场景", "办公室直饮机安装现场", "员工接水使用场景"],
                        "caption": "多场景应用",
                        "image_generation_prompts": ["企业茶水间", "办公室安装现场", "员工接水场景"],
                    },
                    {"type": "divider"},
                    {"type": "cta", "text": "欢迎预约企业饮水方案咨询。", "button_text": "获取方案"},
                ],
                "seo_keywords": ["DeepSeek", "公众号", "企业饮水"],
                "audit_notes": [
                    "直接来自用户输入：名士K2智能直饮机、企业饮水、智能管理。",
                    "合理扩写：办公室饮水体验与运营效率。",
                    "发布前建议人工核对产品参数。",
                ],
            }

        with patch.dict(
            "os.environ",
            {
                "WECHAT_AI_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "deepseek-test-key",
                "DEEPSEEK_MODEL": "deepseek-v4-flash",
            },
            clear=False,
        ):
            with patch("wechat_ai.generator.call_deepseek_article_api", side_effect=fake_deepseek_call):
                article = create_article(
                    conn,
                    {
                        "content_type": "new_product",
                        "product_name": "名士K2智能直饮机",
                        "key_points": ["企业饮水", "智能管理"],
                        "target_audience": "企业运营人员",
                        "tone": "专业",
                        "image_requirement": "产品图",
                        "cta": "预约咨询",
                        "template_id": 1,
                    },
                    api_key="deepseek-test-key",
                )

        self.assertEqual(article["generation_mode"], "api")
        self.assertEqual(article["generation_mode_label"], "真实模型生成")
        self.assertIn("DeepSeek", article["title"])
        self.assertIn("DeepSeek blocks JSON", article["markdown"])
        self.assertIn("从企业饮水效率切入", article["html"])
        self.assertIn("<img", article["html"])
        self.assertTrue(any("直接来自用户输入" in note for note in article["audit_notes"]))
        self.assertEqual(article["blocks"][0]["type"], "heading")
        self.assertTrue(any("企业办公饮水场景" in slot["placeholder_text"] for slot in article["image_slots"]))
        with patch.dict(
            "os.environ",
            {
                "WECHAT_AI_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "deepseek-test-key",
                "DEEPSEEK_MODEL": "deepseek-v4-flash",
            },
            clear=False,
        ):
            self.assertIn("真实模型生成 · deepseek/deepseek-v4-flash", render_preview_page(conn, article["job_id"]))
        self.assertEqual(captured["api_key"], "deepseek-test-key")
        self.assertEqual(captured["model"], "deepseek-v4-flash")

    def test_blocks_are_persisted_rendered_and_saved_as_wechat_html(self):
        from wechat_ai.service import create_article, get_article, save_blocks
        from wechat_ai.web import render_asset_page, render_preview_page

        conn = self.setup_app()

        def fake_deepseek_call(api_key, model, payload, assets, rewrite_hint=None):
            return {
                "title": "Blocks 结构化文章",
                "digest": "结构化摘要",
                "cover": {"query": "名士K2智能直饮机 企业办公饮水场景", "image_generation_prompt": ""},
                "blocks": [
                    {"type": "heading", "level": 2, "text": "原始小标题"},
                    {"type": "paragraph", "text": "原始正文段落"},
                    {"type": "image", "query": "名士K2智能直饮机 产品外观", "caption": "原始配图", "image_generation_prompt": ""},
                    {"type": "gallery", "queries": ["企业茶水间", "办公室直饮机"], "caption": "原始图组", "image_generation_prompts": []},
                    {"type": "cta", "text": "原始行动引导", "button_text": "预约咨询"},
                ],
                "seo_keywords": ["blocks", "公众号"],
                "audit_notes": ["直接来自用户输入：名士K2。"],
            }

        with patch.dict(
            "os.environ",
            {
                "WECHAT_AI_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "deepseek-test-key",
                "DEEPSEEK_MODEL": "deepseek-v4-flash",
            },
            clear=False,
        ):
            with patch("wechat_ai.generator.call_deepseek_article_api", side_effect=fake_deepseek_call):
                article = create_article(
                    conn,
                    {
                        "content_type": "new_product",
                        "product_name": "名士K2智能直饮机",
                        "key_points": ["企业饮水"],
                        "target_audience": "企业运营人员",
                        "tone": "专业",
                        "image_requirement": "产品图",
                        "cta": "预约咨询",
                        "template_id": 1,
                    },
                    api_key="deepseek-test-key",
                )

        loaded = get_article(conn, article["job_id"])["latest"]
        self.assertEqual(loaded["blocks"][0]["text"], "原始小标题")
        preview = render_preview_page(conn, article["job_id"])
        self.assertIn("Blocks 可编辑预览", preview)
        self.assertIn("data-block-json", preview)
        self.assertIn("saveBlocks", preview)
        self.assertIn("从素材库换图", preview)
        self.assertIn(f"/assets?article={article['job_id']}&slot=0", preview)
        self.assertNotIn('id="block-image-selector-0"', preview)
        self.assertNotIn('class="selector-grid"', preview)

        asset_page = render_asset_page(conn, article["job_id"], 0, f"/articles/{article['job_id']}")
        self.assertIn("正在为文章替换图片", asset_page)
        self.assertIn("不换了，返回文章预览", asset_page)
        self.assertIn("选择替换当前图片", asset_page)
        self.assertIn(f"/articles/{article['job_id']}/replace-image?slot=0", asset_page)
        self.assertIn(f'action="/assets/upload?article={article["job_id"]}&slot=0', asset_page)

        edited = [
            {"type": "heading", "level": 2, "text": "编辑后小标题"},
            {"type": "paragraph", "text": "编辑后正文段落"},
            {"type": "cta", "text": "编辑后行动引导", "button_text": "获取方案"},
        ]
        saved = save_blocks(conn, article["job_id"], edited, api_key="deepseek-test-key")
        self.assertEqual(saved["blocks"][0]["text"], "编辑后小标题")
        self.assertIn("编辑后正文段落", saved["html"])
        self.assertIn("已保存 blocks 编辑内容", saved["audit_notes"][0])

    def test_article_service_supports_history_rewrite_title_and_image_replacement(self):
        from wechat_ai.service import (
            create_article,
            get_article,
            list_articles,
            optimize_title,
            replace_image,
            rewrite_article,
        )

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "holiday_campaign",
                "occasion": "端午节",
                "promotion_detail": "企业饮水方案限时优惠",
                "deadline": "2026-06-18",
                "tone": "活泼、促销感",
                "image_requirement": "节日海报+产品图",
                "cta": "联系顾问领取节日方案",
                "template_id": 2,
            },
            api_key=None,
        )
        self.assertEqual(len(list_articles(conn)), 1)
        self.assertEqual(len(optimize_title(conn, article["job_id"], api_key=None)), 5)
        rewrite = rewrite_article(conn, article["job_id"], "更简洁", api_key=None)
        self.assertIn("更简洁", rewrite["audit_notes"][0])
        replaced = replace_image(conn, article["job_id"], 0, "手动选择/端午促销海报.jpg")
        self.assertEqual(replaced["image_slots"][0]["selected_asset_path"], "手动选择/端午促销海报.jpg")
        loaded = get_article(conn, article["job_id"])
        self.assertGreaterEqual(len(loaded["versions"]), 3)

    def test_web_pages_present_ai_workstation_experience(self):
        from wechat_ai.service import create_article
        from wechat_ai.web import (
            render_asset_page,
            render_home_page,
            render_new_article_page,
            render_preview_page,
            render_template_page,
        )

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "产品图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )
        pages = {
            "home": render_home_page(conn, api_key=None),
            "new": render_new_article_page(conn, api_key=None),
            "preview": render_preview_page(conn, article["job_id"]),
            "assets": render_asset_page(conn),
        }
        joined = "\n".join(pages.values())
        for text in [
            "AI 助手入口",
            "素材数量",
            "文章生成数量",
            "开始创作",
            "最近生成文章（可折叠）",
            "向导式流程",
            "1 选择内容类型",
            "2 填写内容",
            "3 选择风格模板",
            "4 生成",
            "AI助手正在准备",
            "素材卡片",
            "点击图片放大预览",
            "推荐用途",
            "公众号样式预览",
            "智能匹配结果",
            "模拟生成",
            "复制HTML",
        ]:
            self.assertIn(text, joined)
        self.assertNotIn("C:\\", pages["assets"])
        self.assertNotIn("/tmp/", pages["assets"])
        for bad in ["Dashboard", "Demo", "答辩", "演示系统", "模板数量", 'href="/templates"']:
            self.assertNotIn(bad, joined)
        self.assertNotIn("AI状态面板", pages["home"])

    def legacy_preview_supports_complete_content_optimization_workflow(self):
        from wechat_ai.service import create_article
        from wechat_ai.web import render_new_article_page, render_preview_page

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量", "DPM动态蛋白纳滤"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "封面图+产品图+案例图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )
        new_page = render_new_article_page(conn, api_key=None)
        preview = render_preview_page(conn, article["job_id"])
        generated = article["html"]

        for text in [
            "Step1 选择内容类型",
            "Step2 填写内容",
            "Step3 选择风格模板",
            "Step4 生成文章",
            "内容类型卡片",
            "生成中 AI 正在分析素材",
            "标题候选1",
            "标题候选5",
            "采用",
            "标题优化弹窗",
            "已应用新标题",
            "请选择改写风格",
            "AI改写弹窗",
            "更专业",
            "更营销",
            "更亲和",
            "更简洁",
            "更有科技感",
            "原版本",
            "改写版本",
            "采用改写版",
            "保留原文",
            "封面图",
            "产品图",
            "参数图",
            "品牌图",
            "更换图片",
            "打开图片选择器",
            "素材库选择器",
            "当前文章已使用的图片清单",
            "最终确认",
            "复制HTML",
            "HTML源码",
            "公众号正文预览优先",
            "左侧优化工具",
            "右侧图片工具",
            "全部素材图片",
            "搜索全部图片",
            "图片分类筛选",
            "点击预览大图",
            "选择替换当前图片",
            "文章结构导航",
            "封面",
            "正文模块",
            "CTA",
            "编辑面板",
        ]:
            self.assertIn(text, new_page + preview)

        self.assertIn("<img", generated)
        self.assertIn("Banner图", generated)
        self.assertIn("产品图", generated)
        self.assertIn("参数图", generated)
        self.assertIn("品牌图", generated)
        self.assertIn("引用块", generated)
        self.assertIn("CTA按钮", generated)
        self.assertIn("重点卖点卡片", generated)
        self.assertNotIn("配图占位：请从素材库补充", generated)
        self.assertIn("K2产品图.jpg", preview)
        self.assertIn("端午促销海报.jpg", preview)
        self.assertIn("朴道logo.png", preview)

    def test_article_preview_focuses_on_final_wechat_output(self):
        from wechat_ai.service import create_article
        from wechat_ai.web import render_preview_page

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量", "IoT智能管理"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "封面图 产品图 参数图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )
        preview = render_preview_page(conn, article["job_id"])

        for text in [
            "公众号正文预览优先",
            "公众号样式预览",
            "复制HTML",
            "保存到公众号草稿箱",
            'id="html-source"',
            "hidden",
            "draft-result",
        ]:
            self.assertIn(text, preview)

        for hidden_text in [
            "Markdown 正文",
            "HTML源码",
            "文章结构导航",
            "审核要点",
            "当前文章已使用的图片清单",
            "标题优化",
            "AI改写",
            "图片调整",
            "更换图片",
            "素材库选择器",
            "AI状态面板",
            "文章质量评分",
            "右侧图片工具",
            "编辑面板",
        ]:
            self.assertNotIn(hidden_text, preview)

        self.assertIn("<img", article["html"])

    def test_asset_library_has_detail_drawer_filters_and_enterprise_copy(self):
        from wechat_ai.web import parse_multipart_uploads, render_asset_page, save_uploaded_image

        conn = self.setup_app()
        upload_root = self.make_db().parent / "uploads"
        saved = save_uploaded_image(conn, "企业新图.png", b"fake uploaded image", upload_root)
        self.assertTrue(saved.exists())
        uploaded = conn.execute("select type from assets where path like ?", ("%企业新图.png",)).fetchone()
        self.assertEqual(uploaded["type"], "image")
        boundary = "batch-boundary"
        multipart_body = (
            b"--batch-boundary\r\n"
            b'Content-Disposition: form-data; name="asset_file"; filename="one.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
            b"image-one\r\n"
            b"--batch-boundary\r\n"
            b'Content-Disposition: form-data; name="asset_file"; filename="two.jpg"\r\n'
            b"Content-Type: image/jpeg\r\n\r\n"
            b"image-two\r\n"
            b"--batch-boundary--\r\n"
        )
        uploads = parse_multipart_uploads(multipart_body, f"multipart/form-data; boundary={boundary}")
        self.assertEqual([item[0] for item in uploads], ["one.png", "two.jpg"])
        self.assertEqual([item[1] for item in uploads], [b"image-one", b"image-two"])
        page = render_asset_page(conn)
        for text in [
            "搜索素材",
            "分类筛选",
            "用途筛选",
            "上传图片",
            'enctype="multipart/form-data"',
            'accept="image/*"',
            "multiple",
            "支持一次选择多张图片批量上传",
            "当前显示",
            "filterAssets",
            "没有找到匹配素材",
            "素材详情",
            "大图预览",
            "加入文章",
            "作为封面",
            "作为正文配图",
            "推荐用途",
            "点击图片放大预览",
        ]:
            self.assertIn(text, page)
        for bad in ["答辩", "Demo", "演示系统", "图片缩略图 PDF", "PDF资料卡", "K2产品单页.pdf", "000000", ">00<", ">004<"]:
            self.assertNotIn(bad, page)

    def test_wechat_draft_service_supports_mock_mode_and_cover_selection(self):
        from wechat_ai.service import create_article
        from wechat_ai.wechat_draft import WeChatDraftService

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "封面图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )

        result = WeChatDraftService(conn, env={}).publish_article_to_draft(article["job_id"])

        self.assertEqual(result["mode"], "mock")
        self.assertTrue(result["media_id"].startswith("mock_draft_"))
        self.assertIn("获取公众号 access_token", result["steps"])
        self.assertIn("上传封面图", result["steps"])
        self.assertIn("创建草稿", result["steps"])
        self.assertIn("完成", result["steps"])

    def test_wechat_draft_service_real_mode_uses_wechat_api_contract(self):
        from wechat_ai.service import create_article
        from wechat_ai.wechat_draft import WeChatDraftService

        class FakeWeChatDraftService(WeChatDraftService):
            def __init__(self, conn):
                super().__init__(
                    conn,
                    env={
                        "WECHAT_DRAFT_MODE": "real",
                        "WECHAT_APP_ID": "appid",
                        "WECHAT_APP_SECRET": "secret",
                    },
                )
                self.calls = []

            def _get_json(self, url):
                self.calls.append(("GET", url))
                return {"access_token": "token", "expires_in": 7200}

            def _post_file(self, url, file_path, field_name, filename, content_type):
                self.calls.append(("FILE", url, Path(file_path).name, field_name, content_type))
                if "type=thumb" in url:
                    return {"media_id": "thumb_media_id"}
                return {"url": f"https://mmbiz.qpic.cn/{Path(file_path).name}"}

            def _post_json(self, url, payload):
                self.calls.append(("POST", url, payload))
                return {"media_id": "draft_media_id"}

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "封面图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )

        service = FakeWeChatDraftService(conn)
        result = service.publish_article_to_draft(article["job_id"])
        post_call = next(call for call in service.calls if call[0] == "POST")
        draft_payload = post_call[2]

        self.assertEqual(result["mode"], "real")
        self.assertEqual(result["media_id"], "draft_media_id")
        self.assertEqual(draft_payload["articles"][0]["thumb_media_id"], "thumb_media_id")
        self.assertIn("https://mmbiz.qpic.cn/", draft_payload["articles"][0]["content"])
        self.assertNotIn("/asset-thumb/", draft_payload["articles"][0]["content"])

    def test_wechat_draft_error_keeps_wechat_invalid_ip_detail(self):
        from wechat_ai.wechat_draft import WeChatDraftError, WeChatDraftService

        service = WeChatDraftService(
            None,
            env={
                "WECHAT_DRAFT_MODE": "real",
                "WECHAT_APP_ID": "appid",
                "WECHAT_APP_SECRET": "secret",
            },
        )

        with self.assertRaises(WeChatDraftError) as raised:
            service._raise_for_wechat_error(
                {
                    "errcode": 40164,
                    "errmsg": "invalid ip 120.204.117.153 ipv6 ::ffff:120.204.117.153, not in whitelist",
                },
                "access_token 获取失败",
            )

        self.assertIn("IP 未加入微信公众号白名单", str(raised.exception))
        self.assertIn("120.204.117.153", str(raised.exception))

    def test_wechat_draft_ui_exposes_publish_button_and_feedback_panel(self):
        from wechat_ai.service import create_article
        from wechat_ai.web import render_preview_page

        conn = self.setup_app()
        article = create_article(
            conn,
            {
                "content_type": "new_product",
                "product_name": "名士K2智能直饮机",
                "key_points": ["2000G大流量"],
                "target_audience": "企业采购决策者",
                "tone": "专业",
                "image_requirement": "封面图",
                "cta": "预约咨询",
                "template_id": 1,
            },
            api_key=None,
        )
        preview = render_preview_page(conn, article["job_id"])
        for text in [
            "保存到公众号草稿箱",
            "获取公众号 access_token",
            "上传封面图",
            "创建草稿",
            "草稿 media_id",
            "请登录微信公众号后台",
        ]:
            self.assertIn(text, preview)

    def test_cli_input_examples_are_valid_json(self):
        for path in [Path("examples/new_product.json"), Path("examples/holiday_campaign.json")]:
            if path.exists():
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
