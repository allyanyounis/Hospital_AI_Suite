"""
app/utils/tenant_permissions.py
Aramis Health Role Hierarchy, Anti-Privilege Escalation & Scope Enforcement Rules.

Implements:
1. 4-level hospital staff reporting hierarchy (0: Platform Super Admin -> 1: Hospital Admin -> 2: Managers -> 3: HOD -> 4: Staff).
2. Anti-privilege escalation checks (reporting lines, department scopes, no self-promotion).
3. Finance-clinical data segregation (blocking accountants and finance managers from clinical payloads).
4. Tenant audit logging for membership changes.
"""

import logging
from flask import request, abort
from app import db
from app.models import User, HospitalMembership, AdminAuditLog

logger = logging.getLogger(__name__)

# Numeric levels: Lower number = higher authority
ROLE_HIERARCHY_LEVELS = {
    'platform_super_admin': 0,
    'hospital_admin': 1,
    'medical_director': 2,
    'operations_manager': 2,
    'finance_manager': 2,
    'hr_it_manager': 2,
    'hod': 3,
    'doctor': 4,
    'nurse': 4,
    'ot_coordinator': 4,
    'front_desk': 4,
    'accountant': 4,
    'staff_compliance': 4
}

ROLE_DOMAINS = {
    'medical_director': 'clinical',
    'operations_manager': 'operations',
    'finance_manager': 'finance',
    'hr_it_manager': 'hrit',
    'hod': 'clinical',
    'doctor': 'clinical',
    'nurse': 'clinical',
    'ot_coordinator': 'operations',
    'front_desk': 'operations',
    'accountant': 'finance',
    'staff_compliance': 'hrit'
}

FINANCE_ROLES = {'finance_manager', 'accountant'}
CLINICAL_RESTRICTED_FIELDS = {
    'symptoms', 'disease_category', 'notes', 'consultation_transcript',
    'diagnosis', 'advice', 'medicines', 'medical_documents'
}

def get_role_level(role_name: str) -> int:
    """Returns integer rank for role, defaulting to 99 for unknown/patient roles."""
    return ROLE_HIERARCHY_LEVELS.get(role_name, 99)

def get_actor_hospital_membership(user_id: int, hospital_id: int, target_department_id: int | None = None) -> HospitalMembership | None:
    """
    Fetches the highest-ranking active hospital membership for an actor in the given hospital.
    If multiple memberships exist, selects the one with the highest authority (lowest level number),
    preferring a matching department if applicable.
    """
    mems = HospitalMembership.query.filter_by(
        user_id=user_id,
        hospital_id=hospital_id,
        status='active'
    ).all()
    if not mems:
        return None
    
    def sort_key(m):
        dept_match = 0 if (target_department_id and m.department_id == target_department_id) else 1
        return (get_role_level(m.role), dept_match)
    
    mems.sort(key=sort_key)
    return mems[0]

def can_manage_membership(
    actor_user: User | None,
    hospital_id: int,
    target_role: str,
    target_department_id: int | None = None,
    target_user_id: int | None = None
) -> tuple[bool, str]:
    """
    Enforces strict anti-privilege escalation invariants:
    1. Actor cannot manage their own membership (no self-promotion).
    2. Platform Super Admin can manage Hospital Admins (Level 1) and any staff.
    3. In-hospital actor must possess an active membership in the target hospital.
    4. Actor rank must be STRICTLY GREATER than target rank (numerically lower level).
    5. HODs (Level 3) can ONLY manage Level 4 staff assigned to their exact department_id.
    6. Managers (Level 2) can only manage staff within their respective operational domain.
    """
    if actor_user is None:
        return False, "Invalid or missing actor user."

    # 1. No self-promotion / self-modification
    if target_user_id is not None and actor_user.id == target_user_id:
        return False, "Cannot modify your own membership or elevate your own role."

    # 2. Platform Super Admin bypasses within tenant
    if actor_user.role == 'platform_super_admin':
        return True, "Authorized by Platform Super Admin authority."

    # 3. Check actor membership in this hospital (prefer highest authority)
    actor_mem = get_actor_hospital_membership(actor_user.id, hospital_id, target_department_id)
    if not actor_mem:
        return False, f"User {actor_user.id} has no active membership in Hospital {hospital_id}."

    actor_level = get_role_level(actor_mem.role)
    target_level = get_role_level(target_role)

    # 4. Strict level hierarchy: actor level must be strictly less (higher authority)
    if actor_level >= target_level:
        return False, (
            f"Privilege escalation denied: Role '{actor_mem.role}' (level {actor_level}) "
            f"cannot assign or manage role '{target_role}' (level {target_level})."
        )

    # 5. Level 3 (HOD) scope restriction
    if actor_mem.role == 'hod':
        if target_level != 4:
            return False, "Department HOD can only manage Level 4 department staff."
        if not actor_mem.department_id or actor_mem.department_id != target_department_id:
            return False, "Department HOD can only manage staff assigned to their own department."

    # 6. Level 2 Manager domain restriction
    if actor_level == 2:
        actor_domain = ROLE_DOMAINS.get(actor_mem.role)
        target_domain = ROLE_DOMAINS.get(target_role)
        if actor_domain and target_domain and actor_domain != target_domain:
            return False, (
                f"Cross-domain assignment denied: {actor_mem.role} ({actor_domain}) "
                f"cannot manage {target_role} ({target_domain})."
            )

    return True, "Authorized."

def is_finance_role(role_name: str) -> bool:
    """Returns True if the role is a finance role subject to clinical data blinding."""
    return role_name in FINANCE_ROLES

def assert_clinical_access_allowed(role_name: str, resource_name: str = "clinical record"):
    """
    Aborts with 404 and logs audit warning if a finance role attempts to view clinical records.
    (Returns 404 per security requirement to prevent leaking existence of record).
    """
    if is_finance_role(role_name):
        logger.warning(
            f"[FINANCE_RESTRICTION] Finance role '{role_name}' attempted to access "
            f"restricted clinical resource '{resource_name}'. Blocking with 404."
        )
        abort(404)

def sanitize_clinical_payload_for_finance(appointment, role_name: str) -> dict:
    """
    Returns an appointment dictionary with clinical payload fields redacted/hidden
    if the requesting user holds a finance role.
    """
    data = {
        'id': appointment.id,
        'hospital_id': appointment.hospital_id,
        'patient_id': appointment.patient_id,
        'doctor_id': appointment.doctor_id,
        'appointment_type': appointment.appointment_type,
        'appointment_date': appointment.appointment_date.isoformat() if appointment.appointment_date else None,
        'appointment_time': str(appointment.appointment_time) if appointment.appointment_time else None,
        'status': appointment.status,
        'charges': appointment.charges,
        'payment_status': appointment.payment_status,
        'platform_commission_amount': appointment.platform_commission_amount,
        'payment_approved_at': appointment.payment_approved_at.isoformat() if appointment.payment_approved_at else None,
    }

    if is_finance_role(role_name):
        # Explicitly blind clinical payloads
        data['disease_category'] = '[RESTRICTED_FINANCE_VIEW]'
        data['symptoms'] = '[RESTRICTED_FINANCE_VIEW]'
        data['notes'] = '[RESTRICTED_FINANCE_VIEW]'
        data['consultation_transcript'] = None
    else:
        data['disease_category'] = appointment.disease_category
        data['symptoms'] = appointment.symptoms
        data['notes'] = appointment.notes
        data['consultation_transcript'] = appointment.consultation_transcript

    return data

def audit_membership_change(
    actor_id: int,
    hospital_id: int,
    action: str,
    target_user_id: int,
    target_role: str,
    details: str | None = None
) -> AdminAuditLog:
    """Writes an immutable security audit log record for membership changes."""
    ip_addr = request.remote_addr if request else '127.0.0.1'
    log_entry = AdminAuditLog(
        hospital_id=hospital_id,
        admin_id=actor_id,
        action=action,
        target_type='hospital_membership',
        target_id=target_user_id,
        details=f"Role: {target_role}. Details: {details or 'N/A'}",
        ip_address=ip_addr
    )
    db.session.add(log_entry)
    db.session.commit()
    logger.info(
        f"[AUDIT] Actor {actor_id} performed '{action}' on user {target_user_id} "
        f"for role '{target_role}' in Hospital {hospital_id}."
    )
    return log_entry
