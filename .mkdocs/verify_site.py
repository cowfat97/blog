"""Validate the built blog, including publication boundaries. See REFACTOR.md."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.targets.append(attrs['href'])
        elif tag in {'script', 'img'} and 'src' in attrs:
            self.targets.append(attrs['src'])
        elif tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.targets.append(attrs['href'])


def verify(site):
    records = json.loads((site / 'assets/notes-index.json').read_text())
    assert records, 'Missing notes index'
    forbidden_names = {'.env', 'CLAUDE.md', 'AGENTS.md', 'hooks.py', 'mkdocs.yml', 'app.log'}
    for file in site.rglob('*'):
        assert file.name not in forbidden_names, f'Internal file published: {file}'
        assert not any(part in {'.obsidian', '.claude', '.git', 'scripts'} for part in file.relative_to(site).parts), file
    assert list((site / 'assets/stylesheets').glob('main.*.min.css')), 'Theme CSS missing'
    assert list((site / 'assets/javascripts').glob('bundle.*.min.js')), 'Theme JS missing'
    for row in records:
        target = site / unquote(row['url'])
        assert target.is_file() or (target / 'index.html').is_file(), f'Note URL missing: {row["url"]}'
    checked = 0
    for page in ['index.html', '文章/index.html', '专题/index.html', 'about/index.html', '文章/Ideas/index.html']:
        source = site / page
        parser = Links()
        parser.feed(source.read_text())
        for href in parser.targets:
            url = urlsplit(href)
            if url.scheme or url.netloc or not url.path:
                continue
            target = source.parent / unquote(url.path)
            assert target.is_file() or (target / 'index.html').is_file(), f'{page}: broken link {href}'
            checked += 1
    print(f'Built site verified: {len(records)} notes, {checked} local links/assets, theme assets and publication boundaries.')


if __name__ == '__main__':
    verify(Path(sys.argv[1] if len(sys.argv) > 1 else '../site').resolve())
