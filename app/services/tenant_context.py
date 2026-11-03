"""
app/services/tenant_context.py
Aramis Health Multi-Tenant Context & Row-Level Security Integration Service.

Manages tenant identification, transaction-level PostgreSQL RLS context (SET LOCAL app.current_hospital_id),
application-level query scoping, and the dedicated platform super-admin engine.
"""

import logging
from flask import g, session, request, has_request_context, current_app
from sqlalchemy import event, text, create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_platform_engine = None
_PlatformSession = None

def _get_auth_user():
    """Helper to get current authenticated user object or None without flask_login."""
    if not has_request_context():
        return None
    user_id = session.get('user_id')
    if not user_id:
        return None
    if hasattr(g, '_auth_user') and g._auth_user is not None and g._auth_user.id == user_id:
        return g._auth_user
    try:
        from app.models import User
        from app import db
        user = db.session.get(User, user_id)
        g._auth_user = user
        return user
    except Exception:
        return None

def get_platform_engine():
    """
    Returns a dedicated SQLAlchemy engine connected as aramis_platform (with native BYPASSRLS).
    Used EXCLUSIVELY by the platform super admin code path for cross-tenant metrics and operations.
    """
    global _platform_engine, _PlatformSession
    from config import get_platform_db_url
    base_uri = None
    if current_app:
        base_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    plat_url = get_platform_db_url(base_uri)

    if _platform_engine is None or str(_platform_engine.url) != plat_url:
        if _platform_engine is not None:
            _platform_engine.dispose()
        _platform_engine = create_engine(
            plat_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5
        )
        _PlatformSession = sessionmaker(bind=_platform_engine)
        logger.info("[TENANT] Initialized dedicated platform engine (aramis_platform BYPASSRLS).")
    return _platform_engine

def get_platform_session():
    """Returns a new scoped session connected through the platform super admin engine."""
    get_platform_engine()
    return _PlatformSession()

def get_current_hospital_id():
    """
    Resolves the current active hospital ID in order of precedence:
    1. Explicit flask.g override (e.g. g.current_hospital_id)
    2. Fail-closed flag: if g.rls_fail_closed is True, return None immediately.
    3. Session override (session['current_hospital_id'])
    4. Authenticated user's active hospital membership
    5. Request parameter ?hospital_id= or X-Hospital-Id header
    6. Default active hospital (Hospital 1 / Aramis Demo Hospital) for public views.
    """
    # 1 & 2. g overrides
    if hasattr(g, 'current_hospital_id') and g.current_hospital_id is not None:
        return g.current_hospital_id
    if getattr(g, 'rls_fail_closed', False):
        return None

    if has_request_context():
        # 3. Session override
        sess_hid = session.get('current_hospital_id')
        if sess_hid is not None:
            try:
                return int(sess_hid)
            except (ValueError, TypeError):
                pass

        # 4. Authenticated user membership
        auth_u = _get_auth_user()
        if auth_u:
            from app.models import HospitalMembership
            memberships = HospitalMembership.query.filter_by(
                user_id=auth_u.id,
                status='active'
            ).all()
            if memberships:
                primary_hid = memberships[0].hospital_id
                session['current_hospital_id'] = primary_hid
                return primary_hid

        # 5. Request parameter or header
        req_hid = request.args.get('hospital_id') or request.headers.get('X-Hospital-Id')
        if req_hid is not None:
            try:
                parsed_hid = int(req_hid)
                session['current_hospital_id'] = parsed_hid
                return parsed_hid
            except (ValueError, TypeError):
                pass

        # 6. Default fallback to 1 (Aramis Demo Hospital)
        return 1

    try:
        if current_app and current_app.config.get('TESTING'):
            return 1
    except Exception:
        pass

    return None

def set_current_hospital(hospital_id):
    """Explicitly switch the current tenant context for the user session."""
    from app.models import Hospital
    from app import db
    h_id = int(hospital_id)
    hosp = db.session.get(Hospital, h_id)
    if not hosp or hosp.status != 'active':
        raise ValueError(f"Hospital with ID {h_id} not found or inactive.")
    
    if has_request_context():
        session['current_hospital_id'] = h_id
    g.current_hospital_id = h_id
    g.current_hospital = hosp
    return hosp

def get_current_hospital():
    """Returns the Hospital object corresponding to the current tenant context."""
    from app.models import Hospital
    from app import db
    hid = get_current_hospital_id()
    if hid is None:
        return None
    return db.session.get(Hospital, hid)

def get_user_memberships(user_id=None):
    """Returns active HospitalMemberships for the current or specified user."""
    from app.models import HospitalMembership, Hospital
    uid = user_id
    if uid is None:
        auth_u = _get_auth_user()
        if auth_u:
            uid = auth_u.id
    if not uid:
        return []
    return HospitalMembership.query.filter_by(user_id=uid, status='active').all()

def scoped_query(model, hospital_id=None):
    """
    Application-level defense-in-depth scoping helper.
    Ensures query is explicitly filtered by hospital_id on top of PostgreSQL RLS.
    """
    hid = hospital_id if hospital_id is not None else get_current_hospital_id()
    if hid is not None and hasattr(model, 'hospital_id'):
        return model.query.filter(model.hospital_id == hid)
    return model.query

def init_tenant_context(app, db):
    """
    Registers the transaction-level PostgreSQL RLS hook and Flask request hooks.
    """
    @event.listens_for(db.session, 'after_begin')
    def set_rls_tenant_context(session_obj, transaction, connection):
        # Only execute PostgreSQL GUCs if connecting to PostgreSQL
        if connection.dialect.name != 'postgresql':
            return

        hid = get_current_hospital_id()
        uid = None
        if has_request_context():
            uid = session.get('user_id')

        # Fail closed: if hid is None, set empty string '' so NULLIF('', '') evaluates to NULL
        if hid is not None:
            connection.execute(text("SELECT set_config('app.current_hospital_id', :hid, true);"), {"hid": str(hid)})
        else:
            connection.execute(text("SELECT set_config('app.current_hospital_id', '', true);"))

        if uid is not None:
            connection.execute(text("SELECT set_config('app.current_user_id', :uid, true);"), {"uid": str(uid)})
        else:
            connection.execute(text("SELECT set_config('app.current_user_id', '', true);"))

    @app.before_request
    def resolve_tenant_before_request():
        # Handle switcher query parameter ?switch_hospital_id=X
        switch_id = request.args.get('switch_hospital_id')
        if switch_id:
            try:
                set_current_hospital(int(switch_id))
            except Exception as e:
                logger.warning(f"[TENANT] Failed to switch hospital to {switch_id}: {e}")

        hid = get_current_hospital_id()
        g.current_hospital_id = hid
        if hid:
            from app.models import Hospital
            from app import db
            g.current_hospital = db.session.get(Hospital, hid)
        else:
            g.current_hospital = None

    @app.context_processor
    def inject_tenant_context():
        from app.models import Hospital
        try:
            active_hospitals = Hospital.query.filter_by(status='active').all()
        except Exception:
            active_hospitals = []

        user_membs = []
        user_id = session.get('user_id') if has_request_context() else None
        if user_id:
            user_membs = get_user_memberships(user_id)

        return {
            'current_hospital_id': getattr(g, 'current_hospital_id', None),
            'current_hospital': getattr(g, 'current_hospital', None),
            'active_hospitals': active_hospitals,
            'user_memberships': user_membs,
            'brand_name': app.config.get('BRAND_NAME', 'Aramis AI Healthcare Solutions'),
            'brand_short_name': app.config.get('BRAND_SHORT_NAME', 'Aramis Health')
        }
