import argparse
import json
import sys

from .assets import index_assets
from .config import DEFAULT_DB_PATH, get_api_key
from .db import connect, init_db
from .service import create_article, get_article, list_articles
from .web import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wechat_ai", description="微信公众号内容生成与排版 AI 员工")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite 数据库路径")
    sub = parser.add_subparsers(dest="command", required=True)

    reindex = sub.add_parser("reindex", help="重新索引素材库")
    reindex.add_argument("--asset-dir", required=True, help="素材目录")

    generate = sub.add_parser("generate", help="根据 JSON 输入生成文章")
    generate.add_argument("--input", required=True, help="输入 JSON 文件")

    preview = sub.add_parser("preview", help="输出文章 HTML")
    preview.add_argument("--article-id", type=int, required=True)

    sub.add_parser("list", help="列出生成历史")

    serve = sub.add_parser("serve", help="启动本地 Web 工作台")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    init_db(conn)
    if args.command == "reindex":
        count = index_assets(conn, args.asset_dir)
        print(f"已索引素材：{count} 个")
        return 0
    if args.command == "generate":
        payload = json.loads(open(args.input, encoding="utf-8").read())
        article = create_article(conn, payload, get_api_key())
        print(f"文章ID：{article['job_id']}")
        print(f"生成模式：{article['generation_mode_label']}")
        print(f"标题：{article['title']}")
        print("HTML 已生成，可在 Web 工作台预览或使用 preview 命令查看。")
        return 0
    if args.command == "preview":
        article = get_article(conn, args.article_id)
        print(article["latest"]["html"])
        return 0
    if args.command == "list":
        for item in list_articles(conn):
            print(f"{item['id']}\t{item['generation_mode_label']}\t{item['title']}")
        return 0
    if args.command == "serve":
        run_server(args.db, args.host, args.port)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
