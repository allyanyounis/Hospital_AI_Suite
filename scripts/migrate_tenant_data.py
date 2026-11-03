"""
scripts/migrate_tenant_data.py
Executes Step 2.2:
1. Creates "Aramis Demo Hospital" (Tenant 1, Lahore) and migrates all existing data into it.
2. Creates "Aramis City Clinic" (Tenant 2, Islamabad) with its own hierarchy, departments, doctors, and appointments to prove tenant isolation.
"""

import os
import sys
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ['DISABLE_SCHEDULER'] = 'true'

from app import create_app, db
from app.models import (
    User, Hospital, HospitalMembership, Department, Doctor, Patient,
    Appointment, Prescription, PrescriptionMedicine, Review, MedicalDocument,
    Refund, DoctorTransaction, DoctorPayoutRequest, PlatformRevenue, Blog, AdminAuditLog
)

DEMO_PASSWORD_HASH = generate_password_hash("Aramis2026!Demo#")

def run_data_migration():
    from config import get_platform_db_url, normalize_db_url
    mig_url = os.environ.get('MIGRATION_DATABASE_URL')
    if mig_url:
        target_db_url = normalize_db_url(mig_url)
    else:
        target_db_url = get_platform_db_url()

    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = target_db_url
    with app.app_context():
        print("=== STEP 2.2: ARAMIS HEALTH MULTI-TENANT DATA MIGRATION ===")

        # 1. Create or get Aramis Demo Hospital (Tenant 1)
        hosp1 = Hospital.query.filter_by(slug='aramis-demo').first()
        if not hosp1:
            hosp1 = Hospital(
                name="Aramis Demo Hospital",
                slug="aramis-demo",
                city="Lahore",
                address="12-A Medical Enclave, Jail Road, Lahore",
                status="active",
                settings={"commission_percent": 20.0, "currency": "PKR", "timezone": "Asia/Karachi"}
            )
            db.session.add(hosp1)
            db.session.flush()
            print(f"[TENANT 1] Created 'Aramis Demo Hospital' (ID: {hosp1.id})")
        else:
            print(f"[TENANT 1] Found existing 'Aramis Demo Hospital' (ID: {hosp1.id})")

        h1_id = hosp1.id

        # 2. Backfill existing records to Hospital 1
        print("[BACKFILL] Moving existing unassigned records into Hospital 1...")
        Department.query.filter(Department.hospital_id.is_(None)).update({Department.hospital_id: h1_id}, synchronize_session=False)
        Doctor.query.filter(Doctor.hospital_id.is_(None)).update({Doctor.hospital_id: h1_id}, synchronize_session=False)
        Appointment.query.filter(Appointment.hospital_id.is_(None)).update({Appointment.hospital_id: h1_id}, synchronize_session=False)
        Prescription.query.filter(Prescription.hospital_id.is_(None)).update({Prescription.hospital_id: h1_id}, synchronize_session=False)
        MedicalDocument.query.filter(MedicalDocument.hospital_id.is_(None)).update({MedicalDocument.hospital_id: h1_id}, synchronize_session=False)
        Refund.query.filter(Refund.hospital_id.is_(None)).update({Refund.hospital_id: h1_id}, synchronize_session=False)
        DoctorTransaction.query.filter(DoctorTransaction.hospital_id.is_(None)).update({DoctorTransaction.hospital_id: h1_id}, synchronize_session=False)
        DoctorPayoutRequest.query.filter(DoctorPayoutRequest.hospital_id.is_(None)).update({DoctorPayoutRequest.hospital_id: h1_id}, synchronize_session=False)
        PlatformRevenue.query.filter(PlatformRevenue.hospital_id.is_(None)).update({PlatformRevenue.hospital_id: h1_id}, synchronize_session=False)
        Review.query.filter(Review.hospital_id.is_(None)).update({Review.hospital_id: h1_id}, synchronize_session=False)
        Blog.query.filter(Blog.hospital_id.is_(None)).update({Blog.hospital_id: h1_id}, synchronize_session=False)
        AdminAuditLog.query.filter(AdminAuditLog.hospital_id.is_(None)).update({AdminAuditLog.hospital_id: h1_id}, synchronize_session=False)
        db.session.commit()
        print("[BACKFILL] Complete.")

        # 3. Create or get Aramis City Clinic (Tenant 2)
        hosp2 = Hospital.query.filter_by(slug='aramis-city-clinic').first()
        if not hosp2:
            hosp2 = Hospital(
                name="Aramis City Clinic",
                slug="aramis-city-clinic",
                city="Islamabad",
                address="Plot 45, Blue Area, Sector F-6, Islamabad",
                status="active",
                settings={"commission_percent": 15.0, "currency": "PKR", "timezone": "Asia/Karachi"}
            )
            db.session.add(hosp2)
            db.session.flush()
            print(f"[TENANT 2] Created 'Aramis City Clinic' (ID: {hosp2.id})")
        else:
            print(f"[TENANT 2] Found existing 'Aramis City Clinic' (ID: {hosp2.id})")

        h2_id = hosp2.id

        # 4. Create Departments for Hospital 1 and Hospital 2
        core_depts = [
            ("Cardiology", "cardiology", "fas fa-heartbeat", "Advanced cardiovascular diagnostics and interventional care."),
            ("Neurology", "neurology", "fas fa-brain", "Comprehensive neurological evaluation and stroke prevention."),
            ("Pediatrics", "pediatrics", "fas fa-baby", "Pediatric health, developmental screenings, and immunizations.")
        ]
        h1_depts = {}
        for name, slug, icon, desc in core_depts:
            dept = Department.query.filter_by(hospital_id=h1_id, slug=slug).first()
            if not dept:
                dept = Department(
                    hospital_id=h1_id,
                    name=name,
                    slug=slug,
                    icon=icon,
                    description=desc,
                    is_active=True
                )
                db.session.add(dept)
                db.session.flush()
                print(f"[TENANT 1 DEPT] Created {name} (ID: {dept.id})")
            h1_depts[slug] = dept

        h2_depts = {}
        for name, slug, icon, desc in core_depts:
            dept = Department.query.filter_by(hospital_id=h2_id, slug=slug).first()
            if not dept:
                dept = Department(
                    hospital_id=h2_id,
                    name=name,
                    slug=slug,
                    icon=icon,
                    description=desc,
                    is_active=True
                )
                db.session.add(dept)
                db.session.flush()
                print(f"[TENANT 2 DEPT] Created {name} (ID: {dept.id})")
            h2_depts[slug] = dept
        db.session.commit()

        # 5. Helper to get or create demo user
        def get_or_create_user(name, email, phone, cnic, role):
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(
                    name=name,
                    email=email,
                    phone=phone,
                    cnic=cnic,
                    password_hash=DEMO_PASSWORD_HASH,
                    role=role,
                    is_active=True
                )
                db.session.add(u)
                db.session.flush()
            return u

        # Platform Super Admin
        psa = User.query.filter_by(email='superadmin@example.com').first()
        if psa:
            psa.role = 'platform_super_admin'
            db.session.commit()
            print("[ROLE] Updated superadmin@example.com to role 'platform_super_admin'")

        # 6. Seed Complete Hierarchy for Hospital 1 (Aramis Demo Hospital)
        print("\n[HIERARCHY 1] Seeding staff hierarchy for Aramis Demo Hospital...")
        h1_cardio_dept = Department.query.filter_by(hospital_id=h1_id, slug='cardiology').first()

        # Level 1: Hospital Admin
        u_h1_admin = get_or_create_user("Dr. Farooq Qureshi", "admin.demo@aramis.health", "+923007100001", "35201-7100001-1", "admin")
        m_h1_admin = HospitalMembership.query.filter_by(user_id=u_h1_admin.id, hospital_id=h1_id, role='hospital_admin').first()
        if not m_h1_admin:
            m_h1_admin = HospitalMembership(user_id=u_h1_admin.id, hospital_id=h1_id, role='hospital_admin', status='active')
            db.session.add(m_h1_admin)
            db.session.flush()

        # Level 2 Managers (report to Hospital Admin)
        u_h1_md = get_or_create_user("Dr. Naveed Akhtar", "director.demo@aramis.health", "+923007100002", "35201-7100002-1", "admin")
        m_h1_md = HospitalMembership.query.filter_by(user_id=u_h1_md.id, hospital_id=h1_id, role='medical_director').first()
        if not m_h1_md:
            m_h1_md = HospitalMembership(user_id=u_h1_md.id, hospital_id=h1_id, role='medical_director', reports_to_membership_id=m_h1_admin.id, status='active')
            db.session.add(m_h1_md)
            db.session.flush()

        u_h1_ops = get_or_create_user("Salman Tariq", "ops.demo@aramis.health", "+923007100003", "35201-7100003-1", "admin")
        m_h1_ops = HospitalMembership.query.filter_by(user_id=u_h1_ops.id, hospital_id=h1_id, role='operations_manager').first()
        if not m_h1_ops:
            m_h1_ops = HospitalMembership(user_id=u_h1_ops.id, hospital_id=h1_id, role='operations_manager', reports_to_membership_id=m_h1_admin.id, status='active')
            db.session.add(m_h1_ops)
            db.session.flush()

        u_h1_fin = get_or_create_user("Zubair Hassan", "finance.demo@aramis.health", "+923007100004", "35201-7100004-1", "admin")
        m_h1_fin = HospitalMembership.query.filter_by(user_id=u_h1_fin.id, hospital_id=h1_id, role='finance_manager').first()
        if not m_h1_fin:
            m_h1_fin = HospitalMembership(user_id=u_h1_fin.id, hospital_id=h1_id, role='finance_manager', reports_to_membership_id=m_h1_admin.id, status='active')
            db.session.add(m_h1_fin)
            db.session.flush()

        u_h1_hr = get_or_create_user("Sadia Malik", "hr.demo@aramis.health", "+923007100005", "35201-7100005-1", "admin")
        m_h1_hr = HospitalMembership.query.filter_by(user_id=u_h1_hr.id, hospital_id=h1_id, role='hr_it_manager').first()
        if not m_h1_hr:
            m_h1_hr = HospitalMembership(user_id=u_h1_hr.id, hospital_id=h1_id, role='hr_it_manager', reports_to_membership_id=m_h1_admin.id, status='active')
            db.session.add(m_h1_hr)
            db.session.flush()

        # Level 3: HOD (reports to Medical Director)
        # Dr. Tariq Mahmood is an existing user
        u_h1_hod = User.query.filter_by(email="dr.tariq@example.com").first()
        if not u_h1_hod:
            u_h1_hod = get_or_create_user("Dr. Tariq Mahmood", "dr.tariq@example.com", "+923007100006", "35201-7100006-1", "doctor")
        m_h1_hod = HospitalMembership.query.filter_by(user_id=u_h1_hod.id, hospital_id=h1_id, role='hod').first()
        if not m_h1_hod:
            m_h1_hod = HospitalMembership(
                user_id=u_h1_hod.id,
                hospital_id=h1_id,
                role='hod',
                department_id=h1_cardio_dept.id if h1_cardio_dept else None,
                reports_to_membership_id=m_h1_md.id,
                status='active'
            )
            db.session.add(m_h1_hod)
            db.session.flush()
        elif not m_h1_hod.department_id and h1_cardio_dept:
            m_h1_hod.department_id = h1_cardio_dept.id
            db.session.commit()

        # Level 4: Attending Doctor (reports to HOD)
        # Dr. Tariq also has doctor role membership
        m_h1_doc = HospitalMembership.query.filter_by(user_id=u_h1_hod.id, hospital_id=h1_id, role='doctor').first()
        if not m_h1_doc:
            m_h1_doc = HospitalMembership(
                user_id=u_h1_hod.id,
                hospital_id=h1_id,
                role='doctor',
                department_id=h1_cardio_dept.id if h1_cardio_dept else None,
                reports_to_membership_id=m_h1_hod.id,
                consultation_fee_physical=2000.0,
                consultation_fee_video=2500.0,
                status='active'
            )
            db.session.add(m_h1_doc)

        # Level 4: Nurse (reports to HOD)
        u_h1_nurse = get_or_create_user("Nurse Ayesha Bibi", "nurse.demo@aramis.health", "+923007100007", "35201-7100007-1", "nurse")
        m_h1_nurse = HospitalMembership.query.filter_by(user_id=u_h1_nurse.id, hospital_id=h1_id, role='nurse').first()
        if not m_h1_nurse:
            m_h1_nurse = HospitalMembership(
                user_id=u_h1_nurse.id,
                hospital_id=h1_id,
                role='nurse',
                department_id=h1_cardio_dept.id if h1_cardio_dept else None,
                reports_to_membership_id=m_h1_hod.id,
                status='active'
            )
            db.session.add(m_h1_nurse)

        # Level 4: OT Coordinator & Front Desk (report to Operations Manager)
        u_h1_ot = get_or_create_user("Kamran Aslam", "ot.demo@aramis.health", "+923007100008", "35201-7100008-1", "ot_coordinator")
        m_h1_ot = HospitalMembership.query.filter_by(user_id=u_h1_ot.id, hospital_id=h1_id, role='ot_coordinator').first()
        if not m_h1_ot:
            m_h1_ot = HospitalMembership(user_id=u_h1_ot.id, hospital_id=h1_id, role='ot_coordinator', reports_to_membership_id=m_h1_ops.id, status='active')
            db.session.add(m_h1_ot)

        u_h1_fd = get_or_create_user("Fatima Noor", "frontdesk.demo@aramis.health", "+923007100009", "35201-7100009-1", "front_desk")
        m_h1_fd = HospitalMembership.query.filter_by(user_id=u_h1_fd.id, hospital_id=h1_id, role='front_desk').first()
        if not m_h1_fd:
            m_h1_fd = HospitalMembership(user_id=u_h1_fd.id, hospital_id=h1_id, role='front_desk', reports_to_membership_id=m_h1_ops.id, status='active')
            db.session.add(m_h1_fd)

        # Level 4: Accountant (reports to Finance Manager)
        u_h1_acc = get_or_create_user("Imran Javed", "accountant.demo@aramis.health", "+923007100010", "35201-7100010-1", "accountant")
        m_h1_acc = HospitalMembership.query.filter_by(user_id=u_h1_acc.id, hospital_id=h1_id, role='accountant').first()
        if not m_h1_acc:
            m_h1_acc = HospitalMembership(user_id=u_h1_acc.id, hospital_id=h1_id, role='accountant', reports_to_membership_id=m_h1_fin.id, status='active')
            db.session.add(m_h1_acc)

        # Level 4: Staff Compliance (reports to HR/IT Manager)
        u_h1_sc = get_or_create_user("Bilal Mehmood", "compliance.demo@aramis.health", "+923007100011", "35201-7100011-1", "staff_compliance")
        m_h1_sc = HospitalMembership.query.filter_by(user_id=u_h1_sc.id, hospital_id=h1_id, role='staff_compliance').first()
        if not m_h1_sc:
            m_h1_sc = HospitalMembership(user_id=u_h1_sc.id, hospital_id=h1_id, role='staff_compliance', reports_to_membership_id=m_h1_hr.id, status='active')
            db.session.add(m_h1_sc)

        # Also connect all remaining existing doctors to Hospital 1
        for doc in Doctor.query.filter_by(hospital_id=h1_id).all():
            m = HospitalMembership.query.filter_by(user_id=doc.user_id, hospital_id=h1_id, role='doctor').first()
            if not m:
                m = HospitalMembership(
                    user_id=doc.user_id,
                    hospital_id=h1_id,
                    role='doctor',
                    department_id=doc.department_id,
                    reports_to_membership_id=m_h1_md.id,
                    consultation_fee_physical=1800.0,
                    consultation_fee_video=2200.0,
                    status='active'
                )
                db.session.add(m)

        db.session.commit()
        print("[HIERARCHY 1] Seeded complete hierarchy for Aramis Demo Hospital.")

        # 7. Seed Complete Hierarchy for Hospital 2 (Aramis City Clinic)
        print("\n[HIERARCHY 2] Seeding staff hierarchy for Aramis City Clinic (Islamabad)...")
        h2_cardio_dept = h2_depts['cardiology']

        # Level 1: Hospital Admin
        u_h2_admin = get_or_create_user("Dr. Arshad Beg", "admin.city@aramis.health", "+923008200001", "35202-8200001-1", "admin")
        m_h2_admin = HospitalMembership.query.filter_by(user_id=u_h2_admin.id, hospital_id=h2_id, role='hospital_admin').first()
        if not m_h2_admin:
            m_h2_admin = HospitalMembership(user_id=u_h2_admin.id, hospital_id=h2_id, role='hospital_admin', status='active')
            db.session.add(m_h2_admin)
            db.session.flush()

        # Level 2 Managers
        u_h2_md = get_or_create_user("Dr. Shireen Khan", "director.city@aramis.health", "+923008200002", "35202-8200002-1", "admin")
        m_h2_md = HospitalMembership.query.filter_by(user_id=u_h2_md.id, hospital_id=h2_id, role='medical_director').first()
        if not m_h2_md:
            m_h2_md = HospitalMembership(user_id=u_h2_md.id, hospital_id=h2_id, role='medical_director', reports_to_membership_id=m_h2_admin.id, status='active')
            db.session.add(m_h2_md)
            db.session.flush()

        u_h2_ops = get_or_create_user("Taimoor Shah", "ops.city@aramis.health", "+923008200003", "35202-8200003-1", "admin")
        m_h2_ops = HospitalMembership.query.filter_by(user_id=u_h2_ops.id, hospital_id=h2_id, role='operations_manager').first()
        if not m_h2_ops:
            m_h2_ops = HospitalMembership(user_id=u_h2_ops.id, hospital_id=h2_id, role='operations_manager', reports_to_membership_id=m_h2_admin.id, status='active')
            db.session.add(m_h2_ops)
            db.session.flush()

        u_h2_fin = get_or_create_user("Fahad Riaz", "finance.city@aramis.health", "+923008200004", "35202-8200004-1", "admin")
        m_h2_fin = HospitalMembership.query.filter_by(user_id=u_h2_fin.id, hospital_id=h2_id, role='finance_manager').first()
        if not m_h2_fin:
            m_h2_fin = HospitalMembership(user_id=u_h2_fin.id, hospital_id=h2_id, role='finance_manager', reports_to_membership_id=m_h2_admin.id, status='active')
            db.session.add(m_h2_fin)
            db.session.flush()

        u_h2_hr = get_or_create_user("Nida Parveen", "hr.city@aramis.health", "+923008200005", "35202-8200005-1", "admin")
        m_h2_hr = HospitalMembership.query.filter_by(user_id=u_h2_hr.id, hospital_id=h2_id, role='hr_it_manager').first()
        if not m_h2_hr:
            m_h2_hr = HospitalMembership(user_id=u_h2_hr.id, hospital_id=h2_id, role='hr_it_manager', reports_to_membership_id=m_h2_admin.id, status='active')
            db.session.add(m_h2_hr)
            db.session.flush()

        # Level 3 HOD Cardiology (Hospital 2)
        u_h2_hod = get_or_create_user("Dr. Haroon Rasheed", "hod.cardio.city@aramis.health", "+923008200006", "35202-8200006-1", "doctor")
        m_h2_hod = HospitalMembership.query.filter_by(user_id=u_h2_hod.id, hospital_id=h2_id, role='hod').first()
        if not m_h2_hod:
            m_h2_hod = HospitalMembership(
                user_id=u_h2_hod.id,
                hospital_id=h2_id,
                role='hod',
                department_id=h2_cardio_dept.id,
                reports_to_membership_id=m_h2_md.id,
                status='active'
            )
            db.session.add(m_h2_hod)
            db.session.flush()

        # Level 4 Attending Doctor for Hospital 2: Dr. Usman Ali
        u_h2_doc = get_or_create_user("Dr. Usman Ali", "dr.usman@aramis.health", "+923008200012", "35202-8200012-1", "doctor")
        doc_usman = Doctor.query.filter_by(user_id=u_h2_doc.id).first()
        if not doc_usman:
            doc_usman = Doctor(
                user_id=u_h2_doc.id,
                hospital_id=h2_id,
                department_id=h2_cardio_dept.id,
                category="Cardiology",
                specialization="Consultant Cardiologist & Heart Rhythm Specialist",
                experience=11.0,
                pmc_code="77421-M",
                education="MBBS, FCPS (Cardiology), Fellowship Electrophysiology",
                bio="Consultant cardiologist at Aramis City Clinic Islamabad specializing in cardiac rhythm management and heart failure.",
                city="Islamabad",
                location="Aramis City Clinic, Plot 45, Blue Area, Islamabad",
                latitude=33.7167,
                longitude=73.0667,
                is_approved=True,
                is_verified=True,
                profile_completed=True
            )
            db.session.add(doc_usman)
            db.session.flush()

        m_h2_doc = HospitalMembership.query.filter_by(user_id=u_h2_doc.id, hospital_id=h2_id, role='doctor').first()
        if not m_h2_doc:
            m_h2_doc = HospitalMembership(
                user_id=u_h2_doc.id,
                hospital_id=h2_id,
                role='doctor',
                department_id=h2_cardio_dept.id,
                reports_to_membership_id=m_h2_hod.id,
                consultation_fee_physical=2500.0,
                consultation_fee_video=3000.0,
                status='active'
            )
            db.session.add(m_h2_doc)

        # Level 4: Nurse (Hospital 2)
        u_h2_nurse = get_or_create_user("Nurse Zainab Bibi", "nurse.city@aramis.health", "+923008200007", "35202-8200007-1", "nurse")
        m_h2_nurse = HospitalMembership.query.filter_by(user_id=u_h2_nurse.id, hospital_id=h2_id, role='nurse').first()
        if not m_h2_nurse:
            m_h2_nurse = HospitalMembership(
                user_id=u_h2_nurse.id,
                hospital_id=h2_id,
                role='nurse',
                department_id=h2_cardio_dept.id,
                reports_to_membership_id=m_h2_hod.id,
                status='active'
            )
            db.session.add(m_h2_nurse)

        # Level 4: OT Coordinator & Front Desk (Hospital 2)
        u_h2_ot = get_or_create_user("Rehan Siddique", "ot.city@aramis.health", "+923008200008", "35202-8200008-1", "ot_coordinator")
        m_h2_ot = HospitalMembership.query.filter_by(user_id=u_h2_ot.id, hospital_id=h2_id, role='ot_coordinator').first()
        if not m_h2_ot:
            m_h2_ot = HospitalMembership(user_id=u_h2_ot.id, hospital_id=h2_id, role='ot_coordinator', reports_to_membership_id=m_h2_ops.id, status='active')
            db.session.add(m_h2_ot)

        u_h2_fd = get_or_create_user("Saima Gul", "frontdesk.city@aramis.health", "+923008200009", "35202-8200009-1", "front_desk")
        m_h2_fd = HospitalMembership.query.filter_by(user_id=u_h2_fd.id, hospital_id=h2_id, role='front_desk').first()
        if not m_h2_fd:
            m_h2_fd = HospitalMembership(user_id=u_h2_fd.id, hospital_id=h2_id, role='front_desk', reports_to_membership_id=m_h2_ops.id, status='active')
            db.session.add(m_h2_fd)

        # Level 4: Accountant & Staff Compliance (Hospital 2)
        u_h2_acc = get_or_create_user("Kashif Raza", "accountant.city@aramis.health", "+923008200010", "35202-8200010-1", "accountant")
        m_h2_acc = HospitalMembership.query.filter_by(user_id=u_h2_acc.id, hospital_id=h2_id, role='accountant').first()
        if not m_h2_acc:
            m_h2_acc = HospitalMembership(user_id=u_h2_acc.id, hospital_id=h2_id, role='accountant', reports_to_membership_id=m_h2_fin.id, status='active')
            db.session.add(m_h2_acc)

        u_h2_sc = get_or_create_user("Yasmeen Akhtar", "compliance.city@aramis.health", "+923008200011", "35202-8200011-1", "staff_compliance")
        m_h2_sc = HospitalMembership.query.filter_by(user_id=u_h2_sc.id, hospital_id=h2_id, role='staff_compliance').first()
        if not m_h2_sc:
            m_h2_sc = HospitalMembership(user_id=u_h2_sc.id, hospital_id=h2_id, role='staff_compliance', reports_to_membership_id=m_h2_hr.id, status='active')
            db.session.add(m_h2_sc)

        db.session.commit()
        print("[HIERARCHY 2] Seeded complete hierarchy for Aramis City Clinic.")

        # 8. Create Hospital 2 Clinical Visit for Global Patient Ahmed Raza
        pat_ahmed = Patient.query.join(User).filter(User.email == 'patient.ahmed@example.com').first()
        if pat_ahmed and doc_usman:
            appt_city = Appointment.query.filter_by(hospital_id=h2_id, doctor_id=doc_usman.id, patient_id=pat_ahmed.id).first()
            if not appt_city:
                appt_city = Appointment(
                    hospital_id=h2_id,
                    patient_id=pat_ahmed.id,
                    doctor_id=doc_usman.id,
                    appointment_type='physical',
                    appointment_date=date.today() - timedelta(days=2),
                    appointment_time="11:00:00",
                    duration=30,
                    status='completed',
                    payment_status='approved',
                    charges=2500.0,
                    disease_category='Cardiology',
                    symptoms='Hypertensive episode and mild dizziness in Islamabad branch.',
                    notes='Consulted at Aramis City Clinic executive OPD.',
                    patient_completed=True,
                    doctor_completed=True,
                    completed_at=datetime.utcnow() - timedelta(days=2)
                )
                db.session.add(appt_city)
                db.session.flush()

                # Prescription in Hospital 2
                rx_city = Prescription(
                    hospital_id=h2_id,
                    appointment_id=appt_city.id,
                    diagnosis='Primary Hypertension Stage 1',
                    advice='Follow DASH diet, regular BP monitoring morning and evening.'
                )
                db.session.add(rx_city)
                db.session.flush()

                med_city = PrescriptionMedicine(
                    prescription_id=rx_city.id,
                    medicine_name='Amlodipine (Norvasc)',
                    dosage='5mg',
                    frequency='Once Daily',
                    duration='30 Days',
                    instructions='Take in the morning'
                )
                db.session.add(med_city)

                # Review in Hospital 2
                rev_city = Review(
                    hospital_id=h2_id,
                    appointment_id=appt_city.id,
                    patient_id=pat_ahmed.id,
                    doctor_id=doc_usman.id,
                    rating=5,
                    comment='Outstanding clinical facility in Islamabad. Dr. Usman was very thorough.'
                )
                db.session.add(rev_city)
                db.session.commit()
                print(f"[TENANT 2 VISIT] Created Appointment #{appt_city.id} at Aramis City Clinic with Prescription and Review.")

        print("\n=== DATA MIGRATION COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_data_migration()
