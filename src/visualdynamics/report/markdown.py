"""The markdown subset a report's text blocks speak.

Hand-rolled for the same reason the viewers are: nothing third-party
rides inside a deliverable. The subset is what a test report actually
uses — headings with #, **bold**, *italic*, `code`, bullet and numbered
lists, paragraphs on blank lines. Everything is HTML-escaped first, so
a report cannot smuggle markup; what you type is what renders.
"""

from __future__ import annotations

import html
import re

_BOLD = re.compile(r'\*\*(.+?)\*\*')
_ITALIC = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
_CODE = re.compile(r'`([^`]+)`')
_HEADING = re.compile(r'^(#{1,4})\s+(.*)$')
_BULLET = re.compile(r'^[-*]\s+(.*)$')
_NUMBERED = re.compile(r'^\d+[.)]\s+(.*)$')


def _inline(text):
    text = html.escape(text, quote=False)
    text = _CODE.sub(r'<code>\1</code>', text)
    text = _BOLD.sub(r'<strong>\1</strong>', text)
    return _ITALIC.sub(r'<em>\1</em>', text)


def to_html(text: str) -> str:
    """The markdown subset as HTML, one string in, one string out."""
    out, paragraph, listing = [], [], None

    def flush_paragraph() -> None:
        if paragraph:
            out.append('<p>' + '<br>'.join(paragraph) + '</p>')
            paragraph.clear()

    def flush_list() -> None:
        nonlocal listing
        if listing:
            out.append(f'</{listing}>')
            listing = None

    for line in (text or '').splitlines():
        stripped = line.strip()
        heading = _HEADING.match(stripped)
        bullet = _BULLET.match(stripped)
        numbered = _NUMBERED.match(stripped)
        if not stripped:
            flush_paragraph()
            flush_list()
        elif heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1)) + 1   # h1 is the report title
            out.append(f'<h{level}>{_inline(heading.group(2))}</h{level}>')
        elif bullet or numbered:
            flush_paragraph()
            wanted = 'ul' if bullet else 'ol'
            if listing != wanted:
                flush_list()
                out.append(f'<{wanted}>')
                listing = wanted
            out.append(f'<li>{_inline((bullet or numbered).group(1))}</li>')
        else:
            flush_list()
            paragraph.append(_inline(stripped))
    flush_paragraph()
    flush_list()
    return '\n'.join(out)
