import pytest
from app.models import Blog

def test_sanitize_html_strips_xss_vectors():
    """Test ISS-SEC-05: sanitize_html strips script, onerror, javascript:, svg, iframe."""
    from app.utils.sanitize import sanitize_html

    # 1. Script tag stripped
    payload_script = "<p>Hello</p><script>alert('xss')</script>"
    cleaned = sanitize_html(payload_script)
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "<p>Hello</p>" in cleaned

    # 2. Img onerror event handler stripped
    payload_onerror = '<img src="https://example.com/pic.jpg" onerror="alert(\'xss\')">'
    cleaned = sanitize_html(payload_onerror)
    assert "onerror" not in cleaned
    assert 'src="https://example.com/pic.jpg"' in cleaned

    # 3. Javascript: URL scheme stripped
    payload_js_link = '<a href="javascript:alert(1)">Malicious Link</a>'
    cleaned = sanitize_html(payload_js_link)
    assert "javascript:" not in cleaned

    # 4. SVG with onload stripped
    payload_svg = '<svg onload="alert(1)"></svg>'
    cleaned = sanitize_html(payload_svg)
    assert "<svg" not in cleaned
    assert "onload" not in cleaned

    # 5. Iframe stripped
    payload_iframe = '<iframe src="https://evil.com"></iframe>'
    cleaned = sanitize_html(payload_iframe)
    assert "<iframe" not in cleaned

def test_sanitize_html_preserves_legitimate_formatting():
    """Test legitimate rich text tags and structures are preserved."""
    from app.utils.sanitize import sanitize_html

    rich_text = (
        '<h2>Heading Title</h2>'
        '<p>Paragraph with <strong>bold</strong> and <em>italic</em>.</p>'
        '<ul><li>Item 1</li><li>Item 2</li></ul>'
        '<blockquote>Quote block</blockquote>'
        '<table><thead><tr><th>Header</th></tr></thead><tbody><tr><td>Cell</td></tr></tbody></table>'
        '<p><a href="https://quickcare.pk">Safe Link</a></p>'
        '<img src="https://quickcare.pk/image.jpg" alt="Clinical Diagram" width="500">'
    )
    cleaned = sanitize_html(rich_text)
    assert '<h2>Heading Title</h2>' in cleaned
    assert '<strong>bold</strong>' in cleaned
    assert '<em>italic</em>' in cleaned
    assert '<ul><li>Item 1</li><li>Item 2</li></ul>' in cleaned
    assert '<blockquote>Quote block</blockquote>' in cleaned
    assert '<table>' in cleaned
    assert 'href="https://quickcare.pk"' in cleaned
    assert 'alt="Clinical Diagram"' in cleaned

def test_blog_view_sanitizes_stored_db_xss_on_render(client, test_doctor, db_session):
    """Test stored XSS in existing database blog is neutralized when rendered."""
    from datetime import datetime, timedelta

    existing = Blog.query.filter_by(slug='stored-xss-test').first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    xss_content = '<p>Medical advice</p><script>alert("stored-xss")</script><img src="x" onerror="alert(document.cookie)">'
    blog = Blog(
        hospital_id=1,
        doctor_id=test_doctor.doctor_profile.id,
        title='Stored XSS Test Post',
        slug='stored-xss-test',
        content=xss_content,
        excerpt='Excerpt test',
        status='published',
        published_at=datetime.utcnow() - timedelta(days=1)
    )
    db_session.add(blog)
    db_session.commit()
    blog_id = blog.id

    try:
        res = client.get(f'/blogs/{blog_id}')
        assert res.status_code == 200
        assert b"<script>alert" not in res.data
        assert b"stored-xss" not in res.data
        assert b"onerror" not in res.data
        assert b"document.cookie" not in res.data
        assert b"<p>Medical advice</p>" in res.data
    finally:
        db_session.delete(blog)
        db_session.commit()
