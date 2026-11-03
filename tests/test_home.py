import pytest

def test_public_doctors_route_redirect_new_bug_01(client):
    """Test GET /doctors redirects to patients.find_doctors and does not crash with 500."""
    res = client.get('/doctors', follow_redirects=False)
    assert res.status_code == 302
    assert '/patients/find-doctors' in res.headers.get('Location', '')

def test_public_doctors_route_followed_ok(client):
    """Test following GET /doctors redirect renders find_doctors directory with 200 OK."""
    res = client.get('/doctors', follow_redirects=True)
    assert res.status_code == 200
    assert b"Find Doctors" in res.data or b"doctor" in res.data.lower()

def test_navbar_container_div_closed_fe_01():
    """Test ISS-FE-01: Navbar container div in base.html must have matching closing div before </nav>."""
    with open('app/templates/base.html', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    start_idx = next(i for i, l in enumerate(lines) if '<nav' in l)
    end_idx = next(i for i, l in enumerate(lines) if '</nav>' in l)
    nav_lines = [l for i, l in enumerate(lines) if start_idx <= i <= end_idx and ('<nav' in l or '</nav' in l or '<div' in l or '</div' in l)]
    nav_text = ''.join(nav_lines)
    open_divs = nav_text.count('<div')
    close_divs = nav_text.count('</div>')
    assert open_divs == close_divs, f"ISS-FE-01: Navbar has {open_divs} opened divs vs {close_divs} closed divs"
