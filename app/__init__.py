from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from config import config
from datetime import timedelta
import os

# Import db from database module to ensure single instance
from app.database import db

# Initialize extensions
migrate = Migrate()
socketio = SocketIO()
csrf = CSRFProtect()

def create_app(config_name=None):
    """Application factory pattern"""
    flask_app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    flask_app.config.from_object(config[config_name])
    
    # Configure session cookies & configurable lifetime (ISS-SEC-08)
    flask_app.config['SESSION_COOKIE_NAME'] = 'quickcare_session_simple'
    flask_app.config['SESSION_COOKIE_PATH'] = '/'
    flask_app.config['SESSION_COOKIE_DOMAIN'] = None
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Secure cookies on HTTPS or when SESSION_COOKIE_SECURE is enabled
    if flask_app.config.get('PREFERRED_URL_SCHEME') == 'https' or os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes'):
        flask_app.config['SESSION_COOKIE_SECURE'] = True
    else:
        flask_app.config['SESSION_COOKIE_SECURE'] = flask_app.config.get('SESSION_COOKIE_SECURE', False)

    # Session lifetime: default 7 days, configurable via PERMANENT_SESSION_LIFETIME_DAYS
    lifetime_days = int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', 7))
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=lifetime_days)
    flask_app.config['SESSION_COOKIE_EXPIRES'] = timedelta(days=lifetime_days)
    
    # Initialize extensions with app
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    csrf.init_app(flask_app)
    
    # Initialize Aramis Health Multi-Tenant Row-Level Security Context
    from app.services.tenant_context import init_tenant_context
    init_tenant_context(flask_app, db)
    
    # Use threading mode for Python 3.12 compatibility (eventlet is not compatible)
    socketio.init_app(flask_app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)
    
    # Initialize email service
    from app.services.email_service import init_mail
    init_mail(flask_app)
    
    # Initialize background scheduler (for auto-cleanup jobs)
    if not flask_app.config.get('TESTING') and os.environ.get('DISABLE_SCHEDULER', '').lower() not in ('true', '1', 'yes'):
        from app.scheduler import init_scheduler
        init_scheduler(flask_app)

    # Check Agora configuration and log warning if missing
    if not flask_app.config.get('AGORA_APP_ID') or not flask_app.config.get('AGORA_APP_CERTIFICATE'):
        flask_app.logger.warning("Agora video calling is not configured (AGORA_APP_ID or AGORA_APP_CERTIFICATE missing). Video features will be unavailable.")
    
    # Register blueprints
    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.doctors import doctors_bp
    from app.routes.patients import patients_bp
    from app.routes.admin import admin_bp
    from app.routes.appointments import appointments_bp
    from app.routes.blogs import blogs_bp
    from app.routes.qa import qa_bp
    from app.routes.diseases import diseases_bp
    from app.routes.video import video_bp
    from app.routes.prescriptions import prescriptions_bp
    from app.routes.payments import payments_bp
    from app.routes.reviews import reviews_bp
    from app.routes.files import files_bp
    from app.routes.platform_admin import platform_admin_bp
    
    flask_app.register_blueprint(home_bp)
    flask_app.register_blueprint(auth_bp, url_prefix='/auth')
    flask_app.register_blueprint(doctors_bp, url_prefix='/doctors')
    flask_app.register_blueprint(patients_bp, url_prefix='/patients')
    flask_app.register_blueprint(admin_bp, url_prefix='/admin')
    flask_app.register_blueprint(platform_admin_bp)
    flask_app.register_blueprint(appointments_bp, url_prefix='/appointments')
    flask_app.register_blueprint(blogs_bp, url_prefix='/blogs')
    flask_app.register_blueprint(qa_bp, url_prefix='/qa')
    flask_app.register_blueprint(diseases_bp, url_prefix='/diseases')
    flask_app.register_blueprint(video_bp, url_prefix='/video')
    flask_app.register_blueprint(prescriptions_bp)
    flask_app.register_blueprint(payments_bp)
    flask_app.register_blueprint(reviews_bp)
    flask_app.register_blueprint(files_bp)

    @flask_app.before_request
    def block_legacy_private_static_urls():
        from flask import request, abort
        path = request.path
        if path.startswith('/static/prescriptions/'):
            abort(404)
        if path.startswith('/static/uploads/'):
            rel = path[len('/static/uploads/'):]
            private_prefixes = (
                'cnic/', 'degrees/', 'payment_screenshots/', 'medical_documents/',
                'live_photos/', 'prescriptions/', 'refund_proofs/', 'payout_proofs/'
            )
            if any(rel.startswith(p) for p in private_prefixes):
                abort(404)
            allowed_prefixes = ('profile_pictures/', 'blog_covers/', 'blogs/', 'qa_replies/')
            if not any(rel.startswith(p) for p in allowed_prefixes):
                base = os.path.basename(rel)
                private_dir = flask_app.config.get('PRIVATE_UPLOAD_FOLDER', os.path.join(flask_app.instance_path, 'private_uploads'))
                for sub in ('cnic', 'degrees', 'payment_screenshots', 'medical_documents', 'live_photos', 'prescriptions', 'refund_proofs', 'payout_proofs'):
                    if os.path.isfile(os.path.join(private_dir, sub, base)):
                        abort(404)
                if '/' not in rel:
                    from app.models import User
                    is_profile_pic = User.query.filter(User.profile_picture == rel).first() is not None
                    if not is_profile_pic:
                        abort(404)

    @flask_app.after_request
    def prevent_admin_page_cache(response):
        from flask import request
        if request.path.startswith('/admin'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    @flask_app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    from flask_wtf.csrf import CSRFError

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        from flask import request, flash, redirect, url_for, jsonify
        from urllib.parse import urlparse

        # AJAX / JSON requests
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({'error': 'csrf', 'message': e.description or 'CSRF token missing or expired'}), 400

        # Standard browser form submission
        referrer = request.referrer
        if referrer:
            try:
                ref_parsed = urlparse(referrer)
                req_parsed = urlparse(request.url)
                if ref_parsed.netloc == req_parsed.netloc:
                    flash('Your session expired, please try again.', 'warning')
                    return redirect(referrer)
            except Exception:
                pass

        if 'text/html' in request.headers.get('Accept', ''):
            flash('Your session expired, please try again.', 'warning')
            return redirect(url_for('home.index'))

        return jsonify({'error': 'csrf', 'message': e.description or 'CSRF token missing or expired'}), 400
    
    # Import SocketIO events
    with flask_app.app_context():
        import app.services.socketio_events
    
    # Add template context processors
    from app.utils.auth import get_current_user
    
    @flask_app.context_processor
    def inject_user():
        """Make get_current_user available in all templates"""
        from flask import url_for
        from app.utils.timezone import get_pakistan_now, pkt_now_naive
        from app.utils.blog_covers import blog_static_image_path

        def static_asset(filename):
            version = flask_app.config.get('STATIC_ASSET_VERSION', '1')
            return url_for('static', filename=filename, v=version)
        
        def date_time_combine(d, t):
            """Combine date and time objects into datetime"""
            from datetime import datetime
            return datetime.combine(d, t)

        def admin_can(panel_key, action='view'):
            from app.utils.admin_permissions import admin_can as _admin_can
            user = get_current_user()
            return _admin_can(user, panel_key, action)

        def admin_is_super():
            from app.utils.admin_permissions import is_super_admin
            return is_super_admin(get_current_user())

        def admin_display_name():
            from app.utils.admin_permissions import get_staff_role_label, is_super_admin
            user = get_current_user()
            if not user:
                return ''
            if user.role == 'admin' and user.admin_profile and not is_super_admin(user):
                return get_staff_role_label(user.admin_profile)
            return user.name
            
        return dict(
            get_current_user=get_current_user,
            now_local=get_pakistan_now,
            now_pkt_naive=pkt_now_naive,
            date_time_combine=date_time_combine,
            timedelta=timedelta,
            blog_static_image_path=blog_static_image_path,
            static_asset=static_asset,
            admin_can=admin_can,
            admin_is_super=admin_is_super,
            admin_display_name=admin_display_name,
            brand_name=flask_app.config.get('BRAND_NAME', 'Aramis AI Healthcare Solutions'),
            brand_short_name=flask_app.config.get('BRAND_SHORT_NAME', 'Aramis Health'),
            brand_tagline=flask_app.config.get('BRAND_TAGLINE', 'Intelligent Multi-Hospital Clinical Operating System'),
            geocode_api_url=lambda: url_for('home.geocode_lookup'),
            openfreemap_style_url=flask_app.config.get(
                'OPENFREEMAP_STYLE_URL',
                'https://tiles.openfreemap.org/styles/liberty',
            ),
            maps_geocoding_enabled=bool(flask_app.config.get('GEOAPIFY_API_KEY')),
        )
    
    # Add custom Jinja2 filters
    @flask_app.template_filter('appt_status_label')
    def appt_status_label_filter(appointment):
        from app.utils.appointment_status import appointment_status_label
        return appointment_status_label(appointment)

    @flask_app.template_filter('appt_status_badge')
    def appt_status_badge_filter(appointment):
        from app.utils.appointment_status import appointment_status_badge_class
        return appointment_status_badge_class(appointment)

    @flask_app.template_filter('format_phone')
    def format_phone_filter(phone):
        """Format phone number with +92 prefix and proper spacing
        
        Args:
            phone: Phone number string (e.g., '3001234567' or '+923001234567')
        
        Returns:
            Formatted phone number (e.g., '+92 300 1234567')
        """
        if not phone:
            return ''
        
        # Remove any existing spaces, dashes, or +92 prefix
        phone_clean = str(phone).replace(' ', '').replace('-', '').replace('+92', '')
        
        # If phone is already clean (10 digits), format it
        if phone_clean.isdigit() and len(phone_clean) == 10:
            # Format as: +92 XXX XXXXXXX (e.g., +92 300 1234567)
            return f'+92 {phone_clean[:3]} {phone_clean[3:]}'
        elif phone_clean.isdigit() and len(phone_clean) == 11 and phone_clean.startswith('0'):
            # Remove leading 0 and format (e.g., 03001234567 -> +92 300 1234567)
            phone_clean = phone_clean[1:]
            return f'+92 {phone_clean[:3]} {phone_clean[3:]}'
        else:
            # Return as is if format is unexpected
            return phone
    
    # Create upload directory
    upload_dir = os.path.join('app', 'static', 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    @flask_app.cli.command('seed-demo')
    def seed_demo_cli():
        """Seed fresh demo dataset."""
        from scripts.seed_demo import seed_demo_data
        seed_demo_data(flask_app)

    return flask_app
