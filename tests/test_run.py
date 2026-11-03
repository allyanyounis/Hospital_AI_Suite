import os

def test_dev_server_default_host_is_loopback(monkeypatch):
    """Test dev server host defaults to 127.0.0.1 unless BIND_ALL_INTERFACES=true."""
    monkeypatch.delenv('BIND_ALL_INTERFACES', raising=False)
    monkeypatch.delenv('FLASK_HOST', raising=False)
    
    bind_all = os.environ.get('BIND_ALL_INTERFACES', 'false').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_HOST', '0.0.0.0' if bind_all else '127.0.0.1')
    assert host == '127.0.0.1'

def test_dev_server_host_bind_all_flag(monkeypatch):
    """Test dev server allows 0.0.0.0 when BIND_ALL_INTERFACES=true."""
    monkeypatch.setenv('BIND_ALL_INTERFACES', 'true')
    bind_all = os.environ.get('BIND_ALL_INTERFACES', 'false').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_HOST', '0.0.0.0' if bind_all else '127.0.0.1')
    assert host == '0.0.0.0'
