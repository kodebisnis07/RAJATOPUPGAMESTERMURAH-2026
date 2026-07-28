"""Minifikasi HTML respons tanpa mengubah kode backend.

Catatan: HTML yang dikirim ke browser tetap dapat dilihat melalui View Source.
Modul ini hanya merapikan/minimalkan hasil render agar tidak mudah dibaca dan
mengurangi ukuran respons.
"""
import re

# Pertahankan blok yang sensitif terhadap spasi atau berisi sintaks tersendiri.
_PROTECTED_BLOCK_RE = re.compile(
    r"<(pre|textarea|script|style)\b[^>]*>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_HTML_COMMENT_RE = re.compile(r"<!--(?!\[if\b).*?-->", flags=re.IGNORECASE | re.DOTALL)
_BETWEEN_TAGS_RE = re.compile(r">\s+<")


def minify_html_document(html: str) -> str:
    """Minify HTML secara konservatif.

    Yang dilakukan:
    - menghapus komentar HTML biasa;
    - menghapus whitespace di antara tag;
    - mempertahankan isi pre, textarea, script, dan style apa adanya.
    """
    if not html or "<" not in html:
        return html

    protected: list[str] = []

    def protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"___RTG_HTML_BLOCK_{len(protected) - 1}___"

    compact = _PROTECTED_BLOCK_RE.sub(protect, html)
    compact = _HTML_COMMENT_RE.sub("", compact)
    compact = _BETWEEN_TAGS_RE.sub("><", compact)
    compact = compact.strip()

    for index, block in enumerate(protected):
        compact = compact.replace(f"___RTG_HTML_BLOCK_{index}___", block)

    return compact
