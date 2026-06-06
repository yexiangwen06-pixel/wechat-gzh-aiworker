import json
import tempfile
import unittest
import zipfile
from pathlib import Path


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
            "templates": render_template_page(conn),
        }
        joined = "\n".join(pages.values())
        for text in [
            "AI 助手入口",
            "AI状态面板",
            "素材数量",
            "模板数量",
            "文章生成数量",
            "开始创作",
            "最近生成文章",
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
            "点击查看完整公众号预览",
            "应用到当前文章",
            "智能匹配结果",
            "推荐内容提示",
            "模拟生成",
            "一键复制HTML",
        ]:
            self.assertIn(text, joined)
        self.assertNotIn("C:\\", pages["assets"])
        self.assertNotIn("/tmp/", pages["assets"])
        for bad in ["Dashboard", "Demo", "答辩", "演示系统"]:
            self.assertNotIn(bad, joined)

    def test_preview_supports_complete_content_optimization_workflow(self):
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

    def test_asset_library_has_detail_drawer_filters_and_enterprise_copy(self):
        from wechat_ai.web import render_asset_page

        conn = self.setup_app()
        page = render_asset_page(conn)
        for text in [
            "搜索素材",
            "分类筛选",
            "用途筛选",
            "素材详情",
            "大图预览",
            "加入文章",
            "作为封面",
            "作为正文配图",
            "PDF资料卡",
            "页数",
            "推荐用途",
            "点击图片放大预览",
        ]:
            self.assertIn(text, page)
        for bad in ["答辩", "Demo", "演示系统", "图片缩略图 PDF", "000000", ">00<", ">004<"]:
            self.assertNotIn(bad, page)

    def test_cli_input_examples_are_valid_json(self):
        for path in [Path("examples/new_product.json"), Path("examples/holiday_campaign.json")]:
            if path.exists():
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
