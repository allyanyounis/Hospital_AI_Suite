"""
app/routes/platform_admin.py
Aramis Health Platform Super Admin Console.

Provides executive cross-tenant management:
1. Cross-tenant dashboard metrics via the dedicated aramis_platform engine (BYPASSRLS).
2. Hospital tenant onboarding, configuration, and suspension.
3. Hospital Admin onboarding and privilege assignment.
4. Comprehensive audit logging of platform-level events.
"""

from functools import wraps
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, abort
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Hospital, HospitalMembership, Doctor, Appointment, Department, AdminAuditLog
from app.services.tenant_context import get_platform_session
from app.utils.tenant_permissions import audit_membership_change

platform_admin_bp = Blueprint('platform_admin', __name__, url_prefix='/admin/platform')

def platform_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the Aramis Platform Console.', 'warning')
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        
        user = db.session.get(User, session['user_id'])
        if not user or user.role != 'platform_super_admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return re.sub(r'^-+|-+$', '', text)

@platform_admin_bp.route('/')
@platform_admin_bp.route('/dashboard')
@platform_admin_required
def dashboard():
    """Renders cross-tenant platform executive metrics using aramis_platform BYPASSRLS engine."""
    p_session = get_platform_session()
    try:
        hospitals = p_session.query(Hospital).order_by(Hospital.id.asc()).all()
        total_hospitals = len(hospitals)
        active_hospitals_count = sum(1 for h in hospitals if h.status == 'active')
        total_appointments = p_session.query(Appointment).count()
        total_doctors = p_session.query(Doctor).count()
        total_memberships = p_session.query(HospitalMembership).filter_by(status='active').count()

        # Gather per-hospital stats
        hospital_data = []
        for h in hospitals:
            doc_cnt = p_session.query(Doctor).filter_by(hospital_id=h.id).count()
            appt_cnt = p_session.query(Appointment).filter_by(hospital_id=h.id).count()
            dept_cnt = p_session.query(Department).filter_by(hospital_id=h.id).count()
            ha_mem = p_session.query(HospitalMembership).filter_by(hospital_id=h.id, role='hospital_admin', status='active').first()
            ha_user = p_session.get(User, ha_mem.user_id) if ha_mem else None
            hospital_data.append({
                'hospital': h,
                'doctor_count': doc_cnt,
                'appointment_count': appt_cnt,
                'department_count': dept_cnt,
                'hospital_admin': ha_user
            })

        # Recent audit logs
        recent_logs = p_session.query(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(10).all()

        return render_template(
            'platform_admin/dashboard.html',
            total_hospitals=total_hospitals,
            active_hospitals_count=active_hospitals_count,
            total_appointments=total_appointments,
            total_doctors=total_doctors,
            total_memberships=total_memberships,
            hospital_data=hospital_data,
            recent_logs=recent_logs
        )
    finally:
        p_session.close()

@platform_admin_bp.route('/hospitals/new', methods=['GET', 'POST'])
@platform_admin_required
def new_hospital():
    """Provision a new hospital tenant."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        commission = request.form.get('commission_percent', '20.0').strip()

        if not name or not city or not address:
            flash('Hospital Name, City, and Address are required.', 'danger')
            return redirect(url_for('platform_admin.new_hospital'))

        slug = slugify(name)
        p_session = get_platform_session()
        try:
            existing = p_session.query(Hospital).filter_by(slug=slug).first()
            if existing:
                flash(f"A hospital with slug '{slug}' already exists.", 'danger')
                return redirect(url_for('platform_admin.new_hospital'))

            try:
                comm_pct = float(commission)
            except ValueError:
                comm_pct = 20.0

            hosp = Hospital(
                name=name,
                slug=slug,
                city=city,
                address=address,
                status='active',
                settings={
                    'commission_percent': comm_pct,
                    'currency': 'PKR',
                    'timezone': 'Asia/Karachi'
                }
            )
            p_session.add(hosp)
            p_session.commit()

            # Audit log
            log = AdminAuditLog(
                hospital_id=hosp.id,
                admin_id=session.get('user_id'),
                action='create_hospital',
                target_type='hospital',
                target_id=hosp.id,
                details=f"Created hospital tenant '{name}' ({city}) with {comm_pct}% commission.",
                ip_address=request.remote_addr or '127.0.0.1'
            )
            p_session.add(log)
            p_session.commit()

            flash(f"Hospital '{name}' has been successfully provisioned!", 'success')
            return redirect(url_for('platform_admin.dashboard'))
        finally:
            p_session.close()

    return render_template('platform_admin/new_hospital.html')

@platform_admin_bp.route('/hospitals/<int:hospital_id>/toggle-status', methods=['POST'])
@platform_admin_required
def toggle_hospital_status(hospital_id: int):
    """Toggle hospital status between active and suspended."""
    p_session = get_platform_session()
    try:
        hosp = p_session.get(Hospital, hospital_id)
        if not hosp:
            flash(f"Hospital {hospital_id} not found.", 'danger')
            return redirect(url_for('platform_admin.dashboard'))

        new_status = 'suspended' if hosp.status == 'active' else 'active'
        hosp.status = new_status
        p_session.commit()

        log = AdminAuditLog(
            hospital_id=hosp.id,
            admin_id=session.get('user_id'),
            action='toggle_hospital_status',
            target_type='hospital',
            target_id=hosp.id,
            details=f"Hospital status changed to '{new_status}'.",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        p_session.add(log)
        p_session.commit()

        flash(f"Hospital '{hosp.name}' status updated to '{new_status}'.", 'info')
        return redirect(url_for('platform_admin.dashboard'))
    finally:
        p_session.close()

@platform_admin_bp.route('/hospitals/<int:hospital_id>/onboard-admin', methods=['POST'])
@platform_admin_required
def onboard_hospital_admin(hospital_id: int):
    """Onboard an executive Hospital Admin for the specified hospital."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    cnic = request.form.get('cnic', '').strip()
    password = request.form.get('password', 'Aramis2026!Sec#')

    if not name or not email or not phone or not cnic:
        flash('All fields are required to onboard a Hospital Admin.', 'danger')
        return redirect(url_for('platform_admin.dashboard'))

    p_session = get_platform_session()
    try:
        hosp = p_session.get(Hospital, hospital_id)
        if not hosp:
            flash(f"Hospital {hospital_id} not found.", 'danger')
            return redirect(url_for('platform_admin.dashboard'))

        # Check existing user
        user = p_session.query(User).filter_by(email=email).first()
        if not user:
            user = User(
                name=name,
                email=email,
                phone=phone,
                cnic=cnic,
                password_hash=generate_password_hash(password),
                role='admin',
                is_active=True
            )
            p_session.add(user)
            p_session.flush()

        # Check existing membership
        mem = p_session.query(HospitalMembership).filter_by(
            user_id=user.id,
            hospital_id=hospital_id,
            role='hospital_admin'
        ).first()

        if not mem:
            mem = HospitalMembership(
                user_id=user.id,
                hospital_id=hospital_id,
                role='hospital_admin',
                status='active'
            )
            p_session.add(mem)

        log = AdminAuditLog(
            hospital_id=hospital_id,
            admin_id=session.get('user_id'),
            action='onboard_hospital_admin',
            target_type='hospital_membership',
            target_id=user.id,
            details=f"Onboarded '{name}' ({email}) as Hospital Admin for '{hosp.name}'.",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        p_session.add(log)
        p_session.commit()

        flash(f"Dr./Mr. {name} successfully assigned as Hospital Admin for '{hosp.name}'.", 'success')
        return redirect(url_for('platform_admin.dashboard'))
    finally:
        p_session.close()
