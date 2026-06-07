import json
import mimetypes
import os
import re
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from .service import get_article


TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
UPLOAD_CONTENT_IMAGE_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"


class WeChatDraftError(RuntimeError):
    def __init__(self, message: str, response: dict | None = None):
        super().__init__(message)
        self.response = response or {}


class WeChatDraftService:
    def __init__(self, conn, env: dict | None = None):
        self.conn = conn
        self.env = os.environ if env is None else env
        self.app_id = self.env.get("WECHAT_APP_ID", "")
        self.app_secret = self.env.get("WECHAT_APP_SECRET", "")
        self.draft_mode = self.env.get("WECHAT_DRAFT_MODE", "mock").lower()
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    @property
    def mode(self) -> str:
        if self.draft_mode == "real":
            return "real"
        if self.app_id and self.app_secret and self.draft_mode != "mock":
            return "real"
        return "mock"

    def get_access_token(self) -> str:
        if self.mode == "mock":
            return "mock_access_token"
        if not self.app_id or not self.app_secret:
            raise WeChatDraftError("AppID 或 AppSecret 未配置")
        now = time.time()
        if self._access_token and now < self._access_token_expires_at:
            return self._access_token
        url = (
            f"{TOKEN_URL}?grant_type=client_credential"
            f"&appid={quote(self.app_id)}&secret={quote(self.app_secret)}"
        )
        data = self._get_json(url)
        self._raise_for_wechat_error(data, "access_token 获取失败")
        token = data.get("access_token")
        if not token:
            raise WeChatDraftError("access_token 获取失败：微信接口未返回 access_token", data)
        self._access_token = token
        self._access_token_expires_at = now + int(data.get("expires_in", 7200)) - 300
        return token

    def upload_thumb_image(self, image_path) -> str:
        path = self._require_existing_image(image_path)
        if self.mode == "mock":
            return f"mock_thumb_{path.stem}"
        token = self.get_access_token()
        url = f"{UPLOAD_MATERIAL_URL}?access_token={quote(token)}&type=thumb"
        data = self._post_file(url, path, "media", path.name, self._content_type(path))
        self._raise_for_wechat_error(data, "封面图上传失败")
        media_id = data.get("media_id")
        if not media_id:
            raise WeChatDraftError("封面图上传失败：微信接口未返回 thumb_media_id", data)
        return media_id

    def upload_article_image(self, image_path) -> str:
        path = self._require_existing_image(image_path)
        if self.mode == "mock":
            return f"https://mock.weixin.qq.com/images/{quote(path.name)}"
        token = self.get_access_token()
        url = f"{UPLOAD_CONTENT_IMAGE_URL}?access_token={quote(token)}"
        data = self._post_file(url, path, "media", path.name, self._content_type(path))
        self._raise_for_wechat_error(data, "正文图片上传失败")
        image_url = data.get("url")
        if not image_url:
            raise WeChatDraftError("正文图片上传失败：微信接口未返回图片 URL", data)
        return image_url

    def create_draft(self, article: dict, thumb_media_id: str | None = None) -> dict:
        latest = article.get("latest", article)
        if thumb_media_id is None:
            thumb_media_id = self.upload_thumb_image(self.select_cover_image(latest))
        content = self.prepare_wechat_content(latest["html"])
        payload = {
            "articles": [
                {
                    "title": latest["title"],
                    "author": "",
                    "digest": self._digest(latest.get("markdown", "")),
                    "content": content,
                    "content_source_url": "",
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        if self.mode == "mock":
            return {
                "media_id": f"mock_draft_{latest.get('job_id', 'article')}_{uuid.uuid4().hex[:8]}",
                "payload": payload,
            }
        token = self.get_access_token()
        data = self._post_json(f"{DRAFT_ADD_URL}?access_token={quote(token)}", payload)
        self._raise_for_wechat_error(data, "draft/add 创建失败")
        media_id = data.get("media_id")
        if not media_id:
            raise WeChatDraftError("draft/add 创建失败：微信接口未返回草稿 media_id", data)
        return {"media_id": media_id, "payload": payload}

    def publish_article_to_draft(self, article_id: int) -> dict:
        article = get_article(self.conn, article_id)
        if not article["latest"]:
            raise WeChatDraftError("当前文章没有可发布版本")
        steps = []
        steps.append("获取公众号 access_token")
        self.get_access_token()
        steps.append("上传封面图")
        cover_path = self.select_cover_image(article["latest"])
        thumb_media_id = self.upload_thumb_image(cover_path)
        steps.append("创建草稿")
        draft = self.create_draft(article, thumb_media_id)
        steps.append("完成")
        return {
            "ok": True,
            "mode": self.mode,
            "media_id": draft["media_id"],
            "steps": steps,
            "message": "请登录微信公众号后台 → 内容与互动 → 草稿箱 查看",
        }

    def select_cover_image(self, latest: dict) -> Path:
        for slot in latest.get("image_slots", []):
            candidate = slot.get("selected_asset_path") or slot.get("recommended_asset_path")
            if candidate and Path(candidate).exists():
                return Path(candidate)
        raise WeChatDraftError("图片不存在：当前文章没有可用封面图或正文图片")

    def prepare_wechat_content(self, html: str) -> str:
        content = html
        for asset_id in sorted(set(re.findall(r"/asset-thumb/(\d+)", html))):
            row = self.conn.execute("select path from assets where id = ?", (int(asset_id),)).fetchone()
            if not row:
                raise WeChatDraftError(f"正文图片不存在：素材 ID {asset_id} 未找到")
            image_url = self.upload_article_image(row["path"])
            content = content.replace(f"/asset-thumb/{asset_id}", image_url)
        return content

    def _get_json(self, url: str) -> dict:
        with urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_file(self, url: str, file_path, field_name: str, filename: str, content_type: str) -> dict:
        boundary = f"----wechat-ai-{uuid.uuid4().hex}"
        path = Path(file_path)
        parts = [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8"),
            path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
        request = Request(
            url,
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _require_existing_image(self, image_path) -> Path:
        path = Path(image_path)
        if not path.exists():
            raise WeChatDraftError(f"图片不存在：{path}")
        return path

    def _content_type(self, path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "image/jpeg"

    def _digest(self, markdown: str) -> str:
        text = re.sub(r"[#>*`\-\s]+", " ", markdown).strip()
        return text[:120] or "由公众号内容 AI 工作台生成的企业运营文章"

    def _masked_config(self) -> str:
        secret = self.app_secret or ""
        if len(secret) >= 8:
            masked_secret = f"{secret[:4]}...{secret[-4:]}"
        else:
            masked_secret = "未配置" if not secret else f"长度{len(secret)}"
        app_id = self.app_id or "未配置"
        return f"当前服务读取 AppID={app_id}，AppSecret={masked_secret}，长度={len(secret)}"

    def _raise_for_wechat_error(self, data: dict, prefix: str) -> None:
        errcode = data.get("errcode")
        if errcode in (None, 0):
            return
        errmsg = data.get("errmsg", "")
        hints = {
            40164: "IP 未加入微信公众号白名单",
            40125: f"AppSecret 无效或与当前 AppID 不匹配；{self._masked_config()}",
            40013: "AppID 无效",
            40001: "access_token 获取失败，请检查 AppSecret",
        }
        hint = hints.get(errcode, errmsg or "微信接口返回错误")
        if errmsg and errmsg not in hint:
            hint = f"{hint}；微信返回：{errmsg}"
        raise WeChatDraftError(f"{prefix}：{hint}（errcode={errcode}）", data)
