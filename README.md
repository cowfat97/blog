# how 的博客

Java、数据库、中间件与大模型开发笔记。

线上阅读：[cowfat97.github.io/blog](https://cowfat97.github.io/blog/)

## 内容入口

- [首页](index.md)：个人介绍、精选笔记与最近维护。
- [笔记库](文章/index.md)：标题与正文搜索、领域筛选与分页。
- [专题阅读](专题/index.md)：Java、RAG、Agent、Qwen 与 vLLM 阅读路线。
- [个人思考](文章/Ideas/index.md)：保留在笔记库分类中。
- [关于](about.md)

## 本地预览

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r .mkdocs/requirements.txt
.venv/bin/python -m unittest discover -s .mkdocs/tests -v
.venv/bin/mkdocs serve -f .mkdocs/mkdocs.yml
```

产物验证：`.venv/bin/python .mkdocs/verify_site.py ../site`。

构建：`.venv/bin/mkdocs build -f .mkdocs/mkdocs.yml`，产物位于仓库外的 `../site/`。

## 写作与发布

文章继续放在 `文章/` 的原分类目录，图片放在 `Pic/`。构建时自动补全知识目录并生成浏览器全文索引，不修改源配置。不依赖后端搜索服务。

可选元数据：

```yaml
---
title: 文章标题
summary: 一两句话说明这篇笔记解决什么问题。
tags:
  - Java
draft: false
---
```

`draft: true` 或 `published: false` 的页面不会进入发布文件、导航与搜索。没有可靠日期的旧笔记不补造发布日期；首页“最近维护”依据 Git 变更顺序生成。

仅发布首页、关于、公众号、文章、专题及指定图片、CSS、JS 资源。内部说明、脚本、编辑器配置与环境变量不属于发布内容。不要把私人附件放入公开图片目录。

推送 `main` 后，GitHub Actions 运行检查、构建并发布到现有 `gh-pages` 分支；PR 只检查与构建。原来的定时导航同步已移除，旧 `scripts/sync_nav.py` 命令转为构建检查。

实现与验证：[重构说明](.mkdocs/REFACTOR.md)。
