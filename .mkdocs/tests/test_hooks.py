"""Publication boundary regression tests; see ../REFACTOR.md."""
import importlib.util
import unittest
import json
from tempfile import TemporaryDirectory
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import PluginCollection
from mkdocs.structure.files import File, Files
from pathlib import Path

spec = importlib.util.spec_from_file_location('hooks', Path(__file__).parents[1] / 'hooks.py')
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


class PublicationTests(unittest.TestCase):
    def test_internal_files_never_publish(self):
        for path in ['.env', '.obsidian/app.json', 'CLAUDE.md', '文章/Java/CLAUDE.md',
                     'scripts/example.py', '.mkdocs/mkdocs.yml', '_components/config.json', 'Pic/secret.txt']:
            with self.subTest(path=path):
                self.assertFalse(hooks.is_public(path))

    def test_file_pipeline_keeps_theme_and_excludes_private_content(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs, theme, site = root / 'docs', root / 'theme', root / 'site'
            files = Files([])
            for name, text in {
                'index.md': '# Home', '文章/Java/public.md': '# Public',
                '文章/Java/draft.md': '---\ndraft: true\n---\n# Hidden',
                '文章/Java/CLAUDE.md': '# Internal', '.env': 'PRIVATE_FIXTURE',
            }.items():
                path = docs / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                files.append(File(name, str(docs), str(site), True))
            files.append(File('assets/stylesheets/theme.css', str(theme), str(site), True))
            config = MkDocsConfig()
            config.docs_dir, config.site_dir = str(docs), str(site)
            config.plugins = PluginCollection()
            config.plugins._current_plugin = None
            result = hooks.on_files(files, config)
            paths = [file.src_uri for file in result]
            self.assertIn('assets/stylesheets/theme.css', paths)
            self.assertNotIn('.env', paths)
            self.assertNotIn('文章/Java/draft.md', paths)
            self.assertNotIn('文章/Java/CLAUDE.md', paths)
            data = json.loads(result.get_file_from_path('assets/notes-index.json').content_string)
            self.assertEqual([row['title'] for row in data], ['Public'])

    def test_public_files_and_drafts(self):
        self.assertTrue(hooks.is_public('文章/Java/集合/List.md'))
        self.assertTrue(hooks.is_public('Pic/avatar.jpeg'))
        self.assertFalse(hooks.is_public('文章/Java/draft.md', '---\ndraft: true\n---\n# Draft'))
        self.assertFalse(hooks.is_public('文章/Java/draft.md', '---\npublished: false\n---\n# Draft'))

    def test_index_contains_body_and_preserves_url(self):
        r = hooks.make_record('文章/Java/集合/List.md', '# List\n\n只在正文中的关键词', '文章/Java/集合/List/')
        self.assertEqual(r['url'], '文章/Java/集合/List/')
        self.assertEqual(r['category'], 'Java')
        self.assertIn('只在正文中的关键词', r['text'])

    def test_home_cards_use_built_urls(self):
        r = hooks.make_record('文章/Java/a.md', '# A', '文章/Java/a/')
        markup = hooks.cards([r])
        self.assertNotIn('.md', markup)
        self.assertIn('/Java/a/', markup)

    def test_code_is_searchable(self):
        text = hooks.plain_text('# Example\n```java\nnewFixedThreadPool(4);\n```')
        self.assertIn('newFixedThreadPool', text)
        self.assertNotIn('```', text)

    def test_code_identifiers_and_markdown_titles(self):
        r = hooks.make_record('文章/LLM/a.md', '# 1\\. 标题\n```python\nmax_model_len = 4096\n```', 'a/')
        self.assertEqual(r['title'], '1. 标题')
        self.assertIn('max_model_len', r['text'])

    def test_encoded_urls_are_not_encoded_twice(self):
        r = hooks.make_record('文章/Java/a.md', '# A', '%E6%96%87/Java/a/')
        self.assertIn('href="%E6%96%87/Java/a/"', hooks.cards([r]))

    def test_metadata_overrides_title_and_summary(self):
        r = hooks.make_record('文章/LLM/a.md', '---\ntitle: 标题\nsummary: 摘要\n---\n# 正文', 'a/')
        self.assertEqual((r['title'], r['summary']), ('标题', '摘要'))


if __name__ == '__main__':
    unittest.main()
