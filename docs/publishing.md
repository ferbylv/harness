# 发布文档站

开源项目主页上那种带搜索、左侧目录、深色主题的网站，几乎都不是手写 HTML。套路是：

```text
仓库里的 Markdown  →  静态站点生成器  →  HTML  →  免费托管
     docs/*.md         MkDocs Material      site/    GitHub Pages
```

Python 项目（FastAPI、Pydantic、httpx、Textual）普遍用 **MkDocs + Material 主题**。JavaScript 项目常用 Docusaurus / VitePress。更老的 Python 库用 Sphinx。本仓库走第一条。

## 本地看

```bash
pip install -e ".[docs]"
mkdocs serve
```

改 `docs/` 下的 Markdown，浏览器 [http://127.0.0.1:8000](http://127.0.0.1:8000) 会热更新。`site/` 是生成结果，不要提交（已在 `.gitignore`）。

只生成、不启动服务：

```bash
mkdocs build
```

## 别人怎么看到：GitHub Pages

1. 把这个仓库推到 GitHub（公开仓库 Pages 免费）。
2. 打开仓库 **Settings → Pages**：
   - Source 选 **GitHub Actions**（本仓库已带 workflow），或
   - 等第一次 `mkdocs gh-deploy` 推送 `gh-pages` 分支后，Source 选 **Deploy from a branch** → `gh-pages` / `/ (root)`。
3. 推送到 `main`（或 `master`）后，[`.github/workflows/docs.yml`](https://github.com/ferbylv/harness/blob/main/.github/workflows/docs.yml) 会执行 `mkdocs gh-deploy --force`。
4. 几分钟后打开：

   `https://<你的用户名>.github.io/<仓库名>/`

   本仓库是 `https://ferbylv.github.io/harness/`。

第一次发布前，改 `mkdocs.yml` 里这三行，和真实仓库一致：

```yaml
repo_url: https://github.com/<user>/<repo>
repo_name: <user>/<repo>
site_url: https://<user>.github.io/<repo>/
```

项目站（`user.github.io/repo/`）必须带仓库名那段路径，否则 CSS / 链接会 404。

## 手动发一次（不经过 Actions）

仓库已经 `git push` 到 GitHub 之后：

```bash
mkdocs gh-deploy
```

它会构建站点、提交到 `gh-pages` 分支并推上去。日常还是让 Actions 在每次 push 时自动发。

## 和「只写 README」的差别

| | README | 文档站 |
| --- | --- | --- |
| 别人打开仓库时看到 | GitHub 渲染的这一页 | 独立域名/Pages 上的多页网站 |
| 搜索、目录、主题 | 没有 | 有 |
| 怎么更新 | 改 Markdown，push | 同样改 Markdown，push 后 CI 重建 HTML |

README 继续当仓库封面；详细指南放 `docs/`，由本站承载。

## 其它托管（可选）

- [Read the Docs](https://readthedocs.org/)：连上 GitHub，选 MkDocs，它帮你构建。URL 形如 `harness.readthedocs.io`。
- Cloudflare Pages / Netlify：构建命令 `mkdocs build`，发布目录 `site`。

本项目默认只用 GitHub Pages，零额外账号。
