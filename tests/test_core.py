import json
import sqlite3
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

    def test_database_initializes_core_tables_and_templates(self):
        from wechat_ai.db import connect, init_db

        db_path = self.make_db()
        conn = connect(db_path)
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
        from wechat_ai.assets import index_assets, search_assets
        from wechat_ai.db import connect, init_db

        db_path = self.make_db()
        conn = connect(db_path)
        init_db(conn)
        indexed = index_assets(conn, self.make_asset_dir())
        self.assertGreaterEqual(indexed, 4)
        image = conn.execute("select category from assets where path like '%海报.jpg'").fetchone()
        self.assertEqual(image[0], "海报")
        hits = search_assets(conn, "K2")
        self.assertTrue(any("K2" in hit["text_excerpt"] or "K2" in hit["path"] for hit in hits))

    def test_simulation_generation_returns_complete_article_and_quality_score(self):
        from wechat_ai.assets import index_assets
        from wechat_ai.db import connect, init_db
        from wechat_ai.service import create_article

        db_path = self.make_db()
        conn = connect(db_path)
        init_db(conn)
        index_assets(conn, self.make_asset_dir())
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
        self.assertIn("配图占位", article["html"])
        self.assertGreaterEqual(len(article["image_slots"]), 1)
        self.assertGreaterEqual(article["quality_score"]["overall_score"], 60)

    def test_article_service_supports_history_rewrite_title_and_image_replacement(self):
        from wechat_ai.assets import index_assets
        from wechat_ai.db import connect, init_db
        from wechat_ai.service import (
            create_article,
            get_article,
            list_articles,
            optimize_title,
            replace_image,
            rewrite_article,
        )

        db_path = self.make_db()
        conn = connect(db_path)
        init_db(conn)
        index_assets(conn, self.make_asset_dir())
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
        titles = optimize_title(conn, article["job_id"], api_key=None)
        self.assertEqual(len(titles), 5)
        rewrite = rewrite_article(conn, article["job_id"], "更简洁", api_key=None)
        self.assertIn("更简洁", rewrite["audit_notes"][0])
        replaced = replace_image(conn, article["job_id"], 0, "手动选择/端午促销海报.jpg")
        self.assertEqual(replaced["image_slots"][0]["selected_asset_path"], "手动选择/端午促销海报.jpg")
        loaded = get_article(conn, article["job_id"])
        self.assertGreaterEqual(len(loaded["versions"]), 3)

    def test_web_pages_are_chinese_and_mark_simulation_mode(self):
        from wechat_ai.assets import index_assets
        from wechat_ai.db import connect, init_db
        from wechat_ai.service import create_article
        from wechat_ai.web import (
            render_asset_page,
            render_home_page,
            render_new_article_page,
            render_preview_page,
            render_template_page,
        )

        db_path = self.make_db()
        conn = connect(db_path)
        init_db(conn)
        index_assets(conn, self.make_asset_dir())
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
        pages = [
            render_home_page(conn, api_key=None),
            render_new_article_page(conn, api_key=None),
            render_preview_page(conn, article["job_id"]),
            render_asset_page(conn),
            render_template_page(conn),
        ]
        joined = "\n".join(pages)
        for text in ["首页", "新建文章", "文章预览", "素材库", "模板"]:
            self.assertIn(text, joined)
        self.assertIn("模拟生成", joined)
        self.assertIn("一键复制HTML", joined)

    def test_cli_input_examples_are_valid_json(self):
        for path in [Path("examples/new_product.json"), Path("examples/holiday_campaign.json")]:
            if path.exists():
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
