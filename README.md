# 公众号内容 AI 工作台

这是一个面向企业运营人员的微信公众号内容生成与排版工作台。用户输入企业资料、产品卖点、目标受众和 CTA 后，系统调用 DeepSeek 生成结构化 `blocks`，自动匹配素材库图片，渲染公众号预览，并支持复制 HTML 或保存到微信公众号草稿箱。

## 核心流程

1. 输入企业资料和文章需求。
2. DeepSeek 返回结构化 `blocks JSON`。
3. 前端根据 blocks 渲染公众号文章预览。
4. 系统根据图片 query 匹配素材库。
5. 用户编辑文字、调整 blocks、替换图片。
6. 点击保存后，后端将 blocks 转成微信公众号 HTML。
7. 复制 HTML，或调用微信公众号草稿接口保存到草稿箱。

## 本地启动

推荐使用项目内启动脚本，它会先清理旧的 `8765` 服务，再启动当前代码：

```powershell
cd C:\Users\20103\Documents\企业ai问题解决
.\公众号内容AI工作台-启动.bat
```

打开：

```text
http://localhost:8765/
```

## 环境变量

复制 `.env.example` 为 `.env`，按需填写：

```env
WECHAT_AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash

WECHAT_APP_ID=
WECHAT_APP_SECRET=
WECHAT_DRAFT_MODE=real
```

未配置 DeepSeek API Key 时，系统会进入模拟生成模式；配置后会调用真实模型。

## Vercel 部署

项目已包含 `vercel.json` 和 `api/index.py`，可部署为 Vercel Python Serverless Function。

Vercel 版本会自动加载 `demo_assets/` 中的演示素材，打开公网链接后就能展示素材库、图片匹配和公众号预览效果。素材库页面也支持临时上传图片，但云端上传文件写入 `/tmp`，不保证长期保存。

详见：

```text
docs/vercel-deployment.md
```

## 交付评价维度

- 流程化：固定从资料输入到公众号预览、编辑、复制 HTML 或保存草稿箱的工作流。
- 标准化：DeepSeek 输出 blocks JSON，前端按统一结构渲染，后端按统一规则转 HTML。
- 可复现：本地脚本、环境变量模板、Vercel 配置、演示素材和部署文档齐全，别人电脑上可以按步骤运行。
