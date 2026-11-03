"""HTML Sanitization utility using nh3 for user-generated rich text."""
from typing import Optional
import nh3

# Allowed HTML tags matching TinyMCE editor output
ALLOWED_TAGS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'ul', 'ol', 'li',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del',
    'a', 'img',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
    'blockquote', 'pre', 'code', 'hr', 'br', 'span', 'sub', 'sup'
}

# Allowed attributes per tag
ALLOWED_ATTRIBUTES = {
    '*': {'class', 'id', 'title'},
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'title', 'width', 'height', 'class'},
    'th': {'scope', 'colspan', 'rowspan'},
    'td': {'colspan', 'rowspan'}
}

# Allowed URL schemes for links and images (strictly excludes javascript:, data:, etc.)
ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}


def sanitize_html(html_content: Optional[str]) -> str:
    """
    Sanitize rich HTML content from user input (e.g. TinyMCE blogs).
    Strips scripts, event handlers (onerror, onload, etc.), javascript: URLs,
    iframes, styles, objects, and unsafe tags/attributes while preserving
    legitimate editor formatting.
    """
    if not html_content:
        return ''

    return nh3.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel='noopener noreferrer'
    )
