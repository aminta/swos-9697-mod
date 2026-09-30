"""Build the GitHub Pages copies of the technical manual from docs/src/.

docs/src/manual.it.html and manual.en.html are the sources (artifact-style pages: <title>, <style>, body, no
<html>/<head>). They must stay in sync: same sections, tables and lists in both languages. This script wraps
each one in a full HTML document, points the language links at the sibling page instead of the claude.ai
artifacts, and adds mermaid.js (the artifact viewer renders mermaid blocks natively, GitHub Pages does not).
Output: docs/index.html (Italian), docs/en.html (English).
"""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), '..', 'docs')
PAGES = {'it': ('index.html', 'https://claude.ai/artifact/58v5iQpxMECsUzG2VHxkjN'),
         'en': ('en.html', 'https://claude.ai/artifact/2GdFS8VJho8AEDk3SryDxG')}
MERMAID = ('<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>\n'
           '<script>mermaid.initialize({startOnLoad:true,theme:matchMedia("(prefers-color-scheme: dark)").matches'
           '?"dark":"default"});</script>\n')


def shape(s):
    """Structure fingerprint: the two languages must match."""
    return [s.count(t) for t in ('<h2', '<h3', '<tr>', '<li>', '<dt>', '<pre', 'class="rule"', 'class="note"')]


def build():
    src = {lang: open(os.path.join(ROOT, 'src', f'manual.{lang}.html'), encoding='utf-8').read() for lang in PAGES}
    assert shape(src['it']) == shape(src['en']), ('IT/EN out of sync', shape(src['it']), shape(src['en']))
    for lang, (out, _) in PAGES.items():
        s = src[lang]
        for other, (other_out, url) in PAGES.items():
            s = s.replace(f'href="{url}"', f'href="{other_out}"')
        head, body = s.split('</style>', 1)
        page = (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
                f'<meta name="viewport" content="width=device-width, initial-scale=1">\n{head}</style>\n</head>\n'
                f'<body>{body}{MERMAID}</body>\n</html>\n')
        assert 'claude.ai/artifact' not in page
        open(os.path.join(ROOT, out), 'w', encoding='utf-8').write(page)
        print(f'docs/{out}: {len(page)} bytes')


if __name__ == '__main__':
    build()
