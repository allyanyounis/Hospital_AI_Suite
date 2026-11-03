import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

def normalize_db_url(url: str | None) -> str | None:
    """Normalize database connection URLs for Psycopg 3 compatibility."""
    if not url:
        return url
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg://', 1)
    if url.startswith('postgresql://') and not url.startswith('postgresql+'):
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

def get_app_db_url(base_uri: str | None = None) -> str:
    """
    Returns database URL for normal application runtime, connecting as aramis_app
    (non-superuser, NOBYPASSRLS) to enforce PostgreSQL Row-Level Security.
    """
    direct_app_url = os.environ.get('APP_DATABASE_URL')
    if direct_app_url:
        return normalize_db_url(direct_app_url)
    
    base_url = base_uri or os.environ.get('DATABASE_URL')
    if not base_url:
        return 'sqlite:///quickcare.db'
    
    if 'postgres' in base_url:
        from urllib.parse import urlparse, quote_plus
        u = urlparse(base_url)
        app_pass = quote_plus(os.environ.get('ARAMIS_APP_PASSWORD', 'AramisApp2026!Sec#'))
        netloc = f"aramis_app:{app_pass}@{u.hostname}"
        if u.port:
            netloc += f":{u.port}"
        u_app = u._replace(netloc=netloc)
        return normalize_db_url(u_app.geturl())
    
    return normalize_db_url(base_url)

def get_platform_db_url(base_uri: str | None = None) -> str:
    """
    Returns database URL for platform super admin cross-tenant auditing,
    connecting as aramis_platform (with BYPASSRLS).
    """
    if not base_uri:
        direct_plat_url = os.environ.get('PLATFORM_DATABASE_URL')
        if direct_plat_url and os.environ.get('FLASK_ENV') != 'testing':
            return normalize_db_url(direct_plat_url)
        
        if os.environ.get('FLASK_ENV') == 'testing' or os.environ.get('TESTING') == 'True':
            base_uri = os.environ.get('APP_TEST_DATABASE_URL') or os.environ.get('TEST_DATABASE_URL')
        else:
            base_uri = os.environ.get('APP_DATABASE_URL') or os.environ.get('DATABASE_URL')
    
    if not base_uri:
        return 'sqlite:///quickcare.db'
    
    if 'postgres' in base_uri:
        from urllib.parse import urlparse, quote_plus
        u = urlparse(base_uri)
        plat_pass = quote_plus(os.environ.get('ARAMIS_PLATFORM_PASSWORD', 'AramisPlatform2026!Sec#'))
        netloc = f"aramis_platform:{plat_pass}@{u.hostname}"
        if u.port:
            netloc += f":{u.port}"
        u_plat = u._replace(netloc=netloc)
        return normalize_db_url(u_plat.geturl())
    
    return normalize_db_url(base_uri)

class Config:
    BRAND_NAME = "Aramis AI Healthcare Solutions"
    BRAND_SHORT_NAME = "Aramis Health"
    BRAND_TAGLINE = "Intelligent Multi-Hospital Clinical Operating System"
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = get_app_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration - Bounded & configurable session lifetime (default 7 days)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_NAME = 'quickcare_session_simple'
    SESSION_COOKIE_PATH = '/'
    
    session_lifetime_days = int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', 7))
    SESSION_COOKIE_EXPIRES = timedelta(days=session_lifetime_days)
    PERMANENT_SESSION_LIFETIME = timedelta(days=session_lifetime_days)
    
    # CSRF Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    PRIVATE_UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'private_uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Static asset cache bust (bump when video-call.js or Agora SDK changes)
    STATIC_ASSET_VERSION = os.environ.get('STATIC_ASSET_VERSION', '20260614')
    DOCTORS_PER_PAGE = 12
    
    # Email configuration (optional — set ENABLE_EMAILS=true to send)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'Aramis Health')
    MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'noreply@aramis.health')
    ENABLE_EMAILS = os.environ.get('ENABLE_EMAILS', 'false').lower() in ('true', '1', 'yes')

    # Safepay payment gateway (sandbox or production — set in .env)
    SAFEPAY_API_KEY = os.environ.get('SAFEPAY_API_KEY', '')
    SAFEPAY_SECRET_KEY = os.environ.get('SAFEPAY_SECRET_KEY', '')
    SAFEPAY_BASE_URL = os.environ.get('SAFEPAY_BASE_URL', 'https://sandbox.api.getsafepay.com')
    SAFEPAY_CHECKOUT_URL = os.environ.get('SAFEPAY_CHECKOUT_URL') or os.environ.get(
        'SAFEPAY_BASE_URL', 'https://sandbox.api.getsafepay.com'
    )
    SAFEPAY_ENVIRONMENT = os.environ.get('SAFEPAY_ENVIRONMENT', 'sandbox')
    
    # Agora Video Calling Configuration
    AGORA_APP_ID = os.environ.get('AGORA_APP_ID', '')
    AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE', '')

    # Agora Cloud Recording: set AGORA_ENABLE_RECORDING=true plus CUSTOMER_ID/SECRET and S3 (or other vendor) keys.
    AGORA_ENABLE_RECORDING = os.environ.get('AGORA_ENABLE_RECORDING', 'false').lower() in ('true', '1', 'yes')
    AGORA_CUSTOMER_ID = os.environ.get('AGORA_CUSTOMER_ID', '')
    AGORA_CUSTOMER_SECRET = os.environ.get('AGORA_CUSTOMER_SECRET', '')
    # Storage for Agora Cloud Recording (see https://docs.agora.io/en/cloud-recording/reference/region-vendor )
    # vendor: 1=Amazon S3, 2=Alibaba, 3=Tencent, 5=Azure, 6=Google, 11=S3-compatible + extensionParams
    AGORA_RECORDING_STORAGE_VENDOR = int(os.environ.get('AGORA_RECORDING_STORAGE_VENDOR', 1))  # 1 = AWS S3
    AGORA_RECORDING_STORAGE_REGION = int(os.environ.get('AGORA_RECORDING_STORAGE_REGION', 0))
    AGORA_RECORDING_STORAGE_BUCKET = os.environ.get('AGORA_RECORDING_STORAGE_BUCKET', '')
    AGORA_RECORDING_STORAGE_ACCESS_KEY = os.environ.get('AGORA_RECORDING_STORAGE_ACCESS_KEY', '')
    AGORA_RECORDING_STORAGE_SECRET_KEY = os.environ.get('AGORA_RECORDING_STORAGE_SECRET_KEY', '')
    # S3-compatible endpoint (required for vendor 11 — DigitalOcean Spaces)
    AGORA_RECORDING_STORAGE_ENDPOINT = os.environ.get('AGORA_RECORDING_STORAGE_ENDPOINT') or os.environ.get(
        'DO_SPACES_ENDPOINT', ''
    )
    AGORA_RECORDING_FILE_PREFIX = os.environ.get('AGORA_RECORDING_FILE_PREFIX', 'recordings')
    # Cloud Recording REST API (use sd-rtn.com if api.agora.io is unreachable from your server)
    AGORA_API_BASE = os.environ.get('AGORA_API_BASE', 'https://api.sd-rtn.com/v1/apps')

    # DigitalOcean Spaces — private bucket playback via boto3 presigned URLs
    DO_SPACES_REGION = os.environ.get('DO_SPACES_REGION', '')
    DO_SPACES_BUCKET = os.environ.get('DO_SPACES_BUCKET', '')
    DO_SPACES_ENDPOINT = os.environ.get('DO_SPACES_ENDPOINT', '')
    DO_SPACES_ACCESS_KEY = os.environ.get('DO_SPACES_ACCESS_KEY', '')
    DO_SPACES_SECRET_KEY = os.environ.get('DO_SPACES_SECRET_KEY', '')
    DO_SPACES_PRESIGN_EXPIRES = int(os.environ.get('DO_SPACES_PRESIGN_EXPIRES', 3600))

    # AI chatbot (Q&A pages)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'openrouter/free')
    OPENROUTER_HTTP_REFERER = os.environ.get('OPENROUTER_HTTP_REFERER', 'http://127.0.0.1:5000')
    OPENROUTER_APP_TITLE = os.environ.get('OPENROUTER_APP_TITLE', 'Quick Care AI')

    # Maps — Geoapify geocoding (tiles use OpenFreeMap, no key required)
    GEOAPIFY_API_KEY = os.environ.get('GEOAPIFY_API_KEY', '')
    OPENFREEMAP_STYLE_URL = os.environ.get(
        'OPENFREEMAP_STYLE_URL',
        'https://tiles.openfreemap.org/styles/liberty',
    )

    # Admin bootstrap (scripts/reset_admin_login.py)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@quickcare.pk')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

    # Accounts: platform commission and refunds (no patient wallet)
    PLATFORM_COMMISSION_PERCENT = float(os.environ.get('PLATFORM_COMMISSION_PERCENT', 20))
    MIN_PAYOUT_PKR = float(os.environ.get('MIN_PAYOUT_PKR', 1000))
    CANCELLATION_FULL_REFUND_HOURS = int(os.environ.get('CANCELLATION_FULL_REFUND_HOURS', 24))
    CANCELLATION_PARTIAL_REFUND_HOURS = int(os.environ.get('CANCELLATION_PARTIAL_REFUND_HOURS', 2))
    PARTIAL_REFUND_PERCENT = int(os.environ.get('PARTIAL_REFUND_PERCENT', 50))
    DROPPED_CALL_MAX_SECONDS = int(os.environ.get('DROPPED_CALL_MAX_SECONDS', 180))

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.environ.get('MIGRATION_DATABASE_URL')) or get_app_db_url()
    TEMPLATES_AUTO_RELOAD = True  # Auto-reload templates in development
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable static file caching in development

class ProductionConfig(Config):
    DEBUG = False
    # False until HTTPS (Phase 4). Set SESSION_COOKIE_SECURE=true in .env after SSL.
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.environ.get('MIGRATION_DATABASE_URL')) or get_app_db_url(os.environ.get('TEST_DATABASE_URL'))
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
