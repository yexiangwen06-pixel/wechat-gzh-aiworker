# Vercel 部署说明

## 部署定位

Vercel 版本用于展示和复现核心工作流：

- 输入企业资料
- 调用 DeepSeek 生成 blocks JSON
- 自动加载仓库内置演示素材
- 渲染公众号预览
- 编辑 blocks
- 复制 HTML

本地版本继续承担完整能力：

- 本地 SQLite 持久化
- 本地素材库批量上传
- 微信公众号草稿箱真实保存

原因是 Vercel 的 Serverless Function 文件系统不是长期持久存储，微信公众号草稿箱接口也可能受到出口 IP 白名单限制。

Vercel 版本仍然保留素材上传入口，适合现场临时添加图片；但上传文件写入 `/tmp`，可能随 Serverless 实例回收而丢失。需要长期稳定素材库时，应迁移到对象存储，例如 OSS、COS、S3 或 Vercel Blob。

## 必需文件

项目已包含：

- `api/index.py`：Vercel Python 入口，复用本地 Web 工作台。
- `vercel.json`：将所有路径转发到 Python 入口。
- `requirements.txt`：声明当前版本无第三方 Python 依赖。
- `.env.example`：环境变量模板。
- `demo_assets/`：云端默认演示素材库。

## Vercel 环境变量

在 Vercel Project Settings → Environment Variables 中配置：

```env
WECHAT_AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-flash
WECHAT_DRAFT_MODE=mock
```

如果要尝试微信公众号草稿箱真实接口，再额外配置：

```env
WECHAT_APP_ID=你的微信公众号 AppID
WECHAT_APP_SECRET=你的微信公众号 AppSecret
WECHAT_DRAFT_MODE=real
```

注意：Vercel 出口 IP 不一定固定，真实草稿箱接口可能因为微信公众号 IP 白名单失败。答辩或企业演示建议使用本地版本完成草稿箱保存。

## 推荐部署步骤

1. 将项目推送到 GitHub。
2. 在 Vercel 导入 GitHub 仓库。
3. Application Preset 使用 Python。
4. 添加上方环境变量。
5. 点击 Deploy。
6. 打开 Vercel 分配的域名，进入首页测试“新建文章”。

## 本地可复现步骤

```powershell
cd C:\Users\20103\Documents\企业ai问题解决
.\公众号内容AI工作台-启动.bat
```

然后访问：

```text
http://localhost:8765/
```

## 评分维度对应

### 流程化

系统固定为：

```text
输入企业资料 → DeepSeek blocks JSON → 公众号预览 → 图片匹配 → 编辑 → 复制 HTML / 保存草稿箱
```

### 标准化

DeepSeek 不直接输出 Markdown 或 HTML，而是输出结构化 blocks。前端只负责渲染，后端只负责转换为微信公众号 HTML，使文章结构、图片位置和 CTA 产出更稳定。

### 可复现

项目提供：

- `.env.example`
- `requirements.txt`
- `vercel.json`
- `api/index.py`
- `demo_assets/`
- 本地启动脚本
- 部署说明

别人拿到项目后，可以先用模拟模式跑完整流程，再配置 DeepSeek 和微信公众号参数。
