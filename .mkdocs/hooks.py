"""Public site generation. Design: REFACTOR.md."""
from __future__ import annotations

import html
from html.parser import HTMLParser
import json
import re
import subprocess
from pathlib import Path

import yaml
import markdown as markdown_parser
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parent.parent
PAGE_ROOTS = {'文章', '专题'}
ROOT_PAGES = {'index.md', 'about.md', '公众号.md'}
INTERNAL = {'CLAUDE.md', 'AGENTS.md', 'README.md'}
ASSETS = {'.css', '.js', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.gif', '.ico', '.avif'}
_records = []


def split_content(text):
    if text.startswith('---\n'):
        parts = text.split('\n---', 1)
        if len(parts) == 2:
            metadata = yaml.safe_load(parts[0][4:]) or {}
            if not isinstance(metadata, dict):
                raise ValueError('文章元数据必须是映射')
            return metadata, parts[1].lstrip('\n')
    return {}, text


def is_public(path, text=''):
    path = Path(path)
    if any(part.startswith('.') for part in path.parts) or path.name in INTERNAL:
        return False
    if path.parts[0] in {'Pic', '_components'}:
        return path.suffix.lower() in ASSETS
    if path.suffix != '.md' or not (path.as_posix() in ROOT_PAGES or path.parts[0] in PAGE_ROOTS):
        return False
    meta, _ = split_content(text)
    return meta.get('draft') is not True and meta.get('published') is not False


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(body):
    parser = _TextExtractor()
    parser.feed(markdown_parser.markdown(body, extensions=['fenced_code', 'tables']))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts).replace('[TOC]', '')).strip()


def make_record(path, text, url):
    meta, body = split_content(text)
    heading = re.search(r'^#\s+(.+)$', body, flags=re.M)
    title = plain_text(str(meta.get('title') or (heading.group(1) if heading else Path(path).stem)))
    content = plain_text(body)
    summary = str(meta.get('description') or meta.get('summary') or content.removeprefix(title).strip()[:140] or '打开笔记查看内容。')
    return {'title': title, 'summary': summary, 'category': Path(path).parts[1],
            'url': url, 'text': content, 'path': path}


def _nav_tree(paths, parent):
    pages, folders = [], {}
    for path in paths:
        rest = Path(path).relative_to(parent)
        if len(rest.parts) == 1:
            if rest.name != 'index.md':
                pages.append({rest.stem: path})
        else:
            folders.setdefault(rest.parts[0], []).append(path)
    result = [str(Path(parent) / 'index.md')] if str(Path(parent) / 'index.md') in paths else []
    result += pages
    order = {'Java': 0, 'LLM': 1, '中间件': 2, '数据库': 3, '408': 4, '软考': 5, 'Ideas': 6}
    for folder, members in sorted(folders.items(), key=lambda item: (order.get(item[0], 99), item[0])):
        result.append({{'Rag': 'RAG', 'Mysql': 'MySQL'}.get(folder, folder): _nav_tree(members, Path(parent) / folder)})
    return result


def on_config(config):
    paths = []
    for file in sorted((ROOT / '文章').rglob('*.md')):
        rel = file.relative_to(ROOT).as_posix()
        if is_public(rel, file.read_text(encoding='utf-8')):
            paths.append(rel)
    config['nav'] = [
        {'首页': 'index.md'}, {'笔记': _nav_tree(paths, Path('文章'))},
        {'专题': '专题/index.md'}, {'思考': '文章/Ideas/index.md'}, {'关于': 'about.md'},
    ]
    return config


def on_files(files, config):
    global _records
    _records = []
    for file in list(files):
        # Theme assets come from the installed theme, outside the content root.
        if file.src_dir is None or Path(file.src_dir).resolve() != Path(config['docs_dir']).resolve():
            continue
        text = Path(file.abs_src_path).read_text(encoding='utf-8') if file.src_uri.endswith('.md') else ''
        if not is_public(file.src_uri, text):
            files.remove(file)
            continue
        if file.src_uri.startswith('文章/') and not file.src_uri.endswith('/index.md'):
            _records.append(make_record(file.src_uri, text, file.url))
    _records.sort(key=lambda r: r['title'].casefold())
    files.append(File.generated(config, 'assets/notes-index.json', content=json.dumps(_records, ensure_ascii=False)))
    return files


def cards(records):
    out = []
    for record in records:
        href = html.escape(record['url'], quote=True)
        out.append(f'<article class="note-card"><span class="eyebrow">{html.escape(record["category"])}</span>'
                   f'<h3><a href="{href}">{html.escape(record["title"])}</a></h3>'
                   f'<p>{html.escape(record["summary"])}</p></article>')
    return '<div class="note-grid">' + ''.join(out) + '</div>'


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != 'index.md':
        return markdown
    featured_paths = ['文章/LLM/Agent/Agent.md', '文章/LLM/Rag/RAG.md', '文章/Java/JVM/JVM 内存结构.md']
    lookup = {r['path']: r for r in _records}
    summaries = [
        ('Agent：工具、记忆与规划', '从 LLM 的能力边界出发，理解 Agent 为什么需要工具、记忆与规划。'),
        ('RAG：从文档到检索', '理解知识库问答的基本链路，以及文档处理、向量检索与生成之间的关系。'),
        ('JVM 内存结构', '梳理方法区、堆、栈、程序计数器和本地方法栈，建立内存结构的整体认识。'),
    ]
    featured = [dict(lookup[path], title=title, summary=summary) for path, (title, summary) in zip(featured_paths, summaries) if path in lookup]
    recent = []
    try:
        history = subprocess.run(['git', '-c', 'core.quotepath=false', 'log', '--format=', '--name-only', '--', '文章'],
                                 cwd=ROOT, capture_output=True, text=True, check=True, timeout=10)
        seen = set()
        for path in history.stdout.splitlines():
            if path in lookup and path not in seen:
                seen.add(path)
                recent.append(lookup[path])
                if len(recent) == 4:
                    break
    except (subprocess.SubprocessError, OSError):
        pass
    recent_markup = cards(recent) if recent else '<p>浏览笔记库，查看各领域的学习记录。</p>'
    return markdown.replace('{{ featured_notes }}', cards(featured)).replace('{{ recent_notes }}', recent_markup).replace('{{ note_count }}', str(len(_records)))
