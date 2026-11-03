"""
scripts/seed_demo.py
Seed fresh, realistic demo dataset for Quick Care Connect V2.
Idempotent and runnable as `flask seed-demo` or `python scripts/seed_demo.py`.
"""
import os
import sys
import secrets
import string
from datetime import date, time, datetime, timedelta
from werkzeug.security import generate_password_hash

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ['DISABLE_SCHEDULER'] = 'true'

from app.models import (
    User, Doctor, Patient, Admin, AdminPanelGrant, Appointment,
    Prescription, Review, Refund, RefundPayoutDetail, MedicalDocument
)
from app.database import db


def _generate_svg(text: str, bg_color: str, fg_color: str = "#ffffff") -> str:
    """Generate a clean SVG circular avatar with initials or medical glyph."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <linearGradient id="g_{text}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_color}" />
      <stop offset="100%" stop-color="{_darken_color(bg_color)}" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="50" fill="url(#g_{text})" />
  <text x="50" y="56" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="34" font-weight="700" fill="{fg_color}" text-anchor="middle" dominant-baseline="middle">{text}</text>
</svg>"""


def _darken_color(hex_color: str) -> str:
    """Slightly darken a hex color for SVG gradient."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return "#1e293b"
    r = max(0, int(hex_color[0:2], 16) - 25)
    g = max(0, int(hex_color[2:4], 16) - 25)
    b = max(0, int(hex_color[4:6], 16) - 25)
    return f"#{r:02x}{g:02x}{b:02x}"


def _write_file_if_missing(filepath: str, content: bytes):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.exists(filepath):
        with open(filepath, 'wb') as f:
            f.write(content)


def seed_demo_data(app=None):
    """Seed comprehensive demo dataset into current database."""
    from flask import current_app
    app = app or current_app

    print("=== SEEDING QUICK CARE V2 DEMO DATASET ===")

    # Ensure directories exist
    profile_pic_dir = os.path.join(app.root_path, 'static', 'uploads', 'profile_pictures')
    priv_base = app.config.get('PRIVATE_UPLOAD_FOLDER', os.path.join(app.instance_path, 'private_uploads'))
    os.makedirs(profile_pic_dir, exist_ok=True)
    for sub in ('cnic', 'degrees', 'payment_screenshots', 'medical_documents', 'prescriptions', 'refund_proofs'):
        os.makedirs(os.path.join(priv_base, sub), exist_ok=True)

    # Write placeholder binary assets for private serving
    _write_file_if_missing(os.path.join(priv_base, 'cnic', 'demo_patient_cnic.jpg'), b'DEMO_PATIENT_CNIC_SECURE_PAYLOAD')
    _write_file_if_missing(os.path.join(priv_base, 'cnic', 'demo_doctor_cnic.jpg'), b'DEMO_DOCTOR_CNIC_SECURE_PAYLOAD')
    _write_file_if_missing(os.path.join(priv_base, 'degrees', 'demo_mbbs_degree.pdf'), b'%PDF-1.4 DEMO_MBBS_ACCREDITATION_RECORD')
    _write_file_if_missing(os.path.join(priv_base, 'payment_screenshots', 'demo_payment_slip.png'), b'DEMO_BANK_TRANSFER_RECEIPT_IMAGE')
    _write_file_if_missing(os.path.join(priv_base, 'prescriptions', 'demo_prescription.pdf'), b'%PDF-1.4 DEMO_OFFICIAL_PRESCRIPTION')
    _write_file_if_missing(os.path.join(priv_base, 'refund_proofs', 'demo_refund_receipt.png'), b'DEMO_REFUND_TRANSFER_CONFIRMATION')

    credentials = []

    def get_or_create_user(name, email, phone, cnic, role, password, avatar_text, bg_color):
        user = User.query.filter_by(email=email).first()
        avatar_filename = f"avatar_{email.split('@')[0]}.svg"
        avatar_path = os.path.join(profile_pic_dir, avatar_filename)
        with open(avatar_path, 'w', encoding='utf-8') as f:
            f.write(_generate_svg(avatar_text, bg_color))

        rel_avatar = f"profile_pictures/{avatar_filename}"

        if not user:
            user = User(
                name=name,
                email=email,
                phone=phone,
                cnic=cnic,
                role=role,
                is_active=True,
                profile_picture=rel_avatar,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            print(f"  + Created User: {name} ({role}) -> {email}")
        else:
            user.name = name
            user.phone = phone
            user.cnic = cnic
            user.role = role
            user.is_active = True
            user.profile_picture = rel_avatar
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            print(f"  * Updated User: {name} ({role}) -> {email}")

        credentials.append({
            'role': role.title(),
            'name': name,
            'email': email,
            'password': password
        })
        return user

    # ── 1. Administrators ──────────────────────────────────────────────────────
    print("\n1. Seeding Administrators...")
    # Super Admin
    super_user = get_or_create_user(
        name="Super Administrator",
        email="superadmin@example.com",
        phone="+92-300-1000001",
        cnic="35201-1000001-1",
        role="platform_super_admin",
        password="Aramis2026!Demo#",
        avatar_text="SA",
        bg_color="#0f172a"
    )
    admin_prof = Admin.query.filter_by(user_id=super_user.id).first()
    if not admin_prof:
        admin_prof = Admin(user_id=super_user.id, admin_level='super')
        db.session.add(admin_prof)
        db.session.commit()

    # Staff Admin 1: Accounts & Payments Officer
    staff1_user = get_or_create_user(
        name="Staff Accounts Officer",
        email="staff.accountant@example.com",
        phone="+92-300-1000002",
        cnic="35201-1000002-1",
        role="admin",
        password="StaffAccounts2026!Demo#",
        avatar_text="AC",
        bg_color="#0ea5e9"
    )
    staff1_prof = Admin.query.filter_by(user_id=staff1_user.id).first()
    if not staff1_prof:
        staff1_prof = Admin(user_id=staff1_user.id, admin_level='staff', staff_role='accountant')
        db.session.add(staff1_prof)
        db.session.commit()
    AdminPanelGrant.query.filter_by(admin_id=staff1_prof.id).delete()
    db.session.add(AdminPanelGrant(admin_id=staff1_prof.id, panel_key='accounts', can_view=True, can_approve=True, can_edit=True))
    db.session.add(AdminPanelGrant(admin_id=staff1_prof.id, panel_key='payments', can_view=True, can_approve=True, can_edit=True))
    db.session.commit()

    # Staff Admin 2: Patient & Doctor Verification Manager
    staff2_user = get_or_create_user(
        name="Staff Support Manager",
        email="staff.support@example.com",
        phone="+92-300-1000003",
        cnic="35201-1000003-1",
        role="admin",
        password="StaffSupport2026!Demo#",
        avatar_text="SU",
        bg_color="#10b981"
    )
    staff2_prof = Admin.query.filter_by(user_id=staff2_user.id).first()
    if not staff2_prof:
        staff2_prof = Admin(user_id=staff2_user.id, admin_level='staff', staff_role='patient_support_manager')
        db.session.add(staff2_prof)
        db.session.commit()
    AdminPanelGrant.query.filter_by(admin_id=staff2_prof.id).delete()
    db.session.add(AdminPanelGrant(admin_id=staff2_prof.id, panel_key='patients', can_view=True, can_edit=True))
    db.session.add(AdminPanelGrant(admin_id=staff2_prof.id, panel_key='doctors', can_view=True, can_approve=True))
    db.session.add(AdminPanelGrant(admin_id=staff2_prof.id, panel_key='appointments', can_view=True))
    db.session.commit()

    # ── 2. 12 Verified Pakistani Doctors ───────────────────────────────────────
    print("\n2. Seeding 12 Verified Doctors across Categories...")
    # Explicitly labeled DEMO city centroid coordinates for demo seeding/offline testing
    DEMO_CITY_COORDS = {
        'Lahore': (31.5204, 74.3587),
        'Karachi': (24.8607, 67.0011),
        'Islamabad': (33.6844, 73.0479),
        'Rawalpindi': (33.5651, 73.0169),
        'Faisalabad': (31.4504, 73.1350),
        'Peshawar': (34.0151, 71.5249),
        'Multan': (30.1575, 71.5249)
    }
    doctors_spec = [
        ("Dr. Tariq Mahmood", "dr.tariq@example.com", "+92-300-3000001", "35201-3000001-1", "Cardiologist", "Cardiology", "Doctors Hospital", "Gulberg, Lahore", 18, 2500, 2000, "10001-P-DEMO", "MBBS, FCPS (Cardiology)", "TM", "#ef4444"),
        ("Dr. Ayesha Siddiqui", "dr.ayesha@example.com", "+92-300-3000002", "35201-3000002-1", "Neurologist", "Neurology", "Shifa International", "H-8, Islamabad", 14, 3000, 2500, "10002-P-DEMO", "MBBS, FCPS (Neurology)", "AS", "#8b5cf6"),
        ("Dr. Muhammad Bilal", "dr.bilal@example.com", "+92-300-3000003", "35201-3000003-1", "Pediatrician", "Pediatrics", "Children's Hospital", "Ferozepur Rd, Lahore", 11, 1800, 1500, "10003-P-DEMO", "MBBS, MCPS (Pediatrics)", "MB", "#3b82f6"),
        ("Dr. Fatima Zahra", "dr.fatima@example.com", "+92-300-3000004", "35201-3000004-1", "Dermatologist", "Dermatology", "Aga Khan University Hospital", "Stadium Rd, Karachi", 9, 2200, 1800, "10004-P-DEMO", "MBBS, MD (Dermatology)", "FZ", "#ec4899"),
        ("Dr. Zainab Raza", "dr.zainab@example.com", "+92-300-3000005", "35201-3000005-1", "Gynecologist", "Gynecology", "Lady Reading Hospital", "Peshawar", 16, 2500, 2000, "10005-P-DEMO", "MBBS, FCPS (Obs & Gynae)", "ZR", "#f43f5e"),
        ("Dr. Hamza Tariq", "dr.hamza@example.com", "+92-300-3000006", "35201-3000006-1", "Orthopedic Surgeon", "Orthopedics", "Ghurki Trust Teaching Hospital", "Jallo, Lahore", 12, 2000, 1700, "10006-P-DEMO", "MBBS, MS (Orthopedics)", "HT", "#f97316"),
        ("Dr. Usman Farooq", "dr.usman@example.com", "+92-300-3000007", "35201-3000007-1", "ENT Specialist", "ENT", "Services Hospital", "Jail Rd, Lahore", 10, 1500, 1200, "10007-P-DEMO", "MBBS, DLO, FCPS", "UF", "#14b8a6"),
        ("Dr. Sana Mir", "dr.sana@example.com", "+92-300-3000008", "35201-3000008-1", "Psychiatrist", "Psychiatry", "Mind Care Clinic", "Clifton, Karachi", 8, 3000, 2500, "10008-P-DEMO", "MBBS, FCPS (Psychiatry)", "SM", "#a855f7"),
        ("Dr. Kamran Akmal", "dr.kamran@example.com", "+92-300-3000009", "35201-3000009-1", "Gastroenterologist", "Gastroenterology", "PIMS Hospital", "G-8, Islamabad", 15, 2800, 2200, "10009-P-DEMO", "MBBS, MRCP (UK), FCPS", "KA", "#059669"),
        ("Dr. Hina Altaf", "dr.hina@example.com", "+92-300-3000010", "35201-3000010-1", "Eye Specialist", "Ophthalmology", "Al-Shifa Trust Eye Hospital", "Rawalpindi", 13, 2000, 1600, "10010-P-DEMO", "MBBS, FCPS (Ophthalmology)", "HA", "#0284c7"),
        ("Dr. Noman Ali", "dr.noman@example.com", "+92-300-3000011", "35201-3000011-1", "Dentist", "Dentistry", "Fatima Memorial Hospital", "Shadman, Lahore", 7, 1500, 1200, "10011-P-DEMO", "BDS, RDS, C-Implants", "NA", "#475569"),
        ("Dr. Rashid Latif", "dr.rashid@example.com", "+92-300-3000012", "35201-3000012-1", "General Physician", "General Medicine", "Mayo Hospital", "Anarkali, Lahore", 20, 1500, 1000, "10012-P-DEMO", "MBBS, FCPS (Internal Medicine)", "RL", "#16a34a"),
    ]

    doctor_models = []
    for (name, email, phone, cnic, category, spec, hosp, loc, exp, phys_price, vid_price, pmc, edu, glyph, color) in doctors_spec:
        user = get_or_create_user(
            name=name, email=email, phone=phone, cnic=cnic, role="doctor",
            password="Doctor2026!Demo#", avatar_text=glyph, bg_color=color
        )
        doc = Doctor.query.filter_by(user_id=user.id).first()

        # Build realistic weekly time_slots JSON matching practice organizer
        weekly_slots = {}
        for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'):
            weekly_slots[day] = {
                'hospital': hosp,
                'location': loc,
                'start_time': '09:00',
                'end_time': '17:00',
                'duration': 30,
                'physical_price': phys_price,
                'video_price': vid_price
            }

        if not doc:
            doc = Doctor(
                user_id=user.id,
                category=category,
                specialization=spec,
                experience=float(exp),
                pmc_code=pmc,
                education=edu,
                bio=f"Senior consultant {category} with {exp} years of clinical practice at {hosp}. Committed to evidence-based healthcare and patient wellness.",
                city=loc.split(',')[-1].strip(),
                location=loc,
                is_approved=True,
                is_verified=True,
                profile_completed=True,
                appeal_status='approved',
                time_slots=weekly_slots,
                balance=15000.0,
                total_earned=45000.0,
                cnic_front_image='cnic/demo_doctor_cnic.jpg',
                cnic_back_image='cnic/demo_doctor_cnic.jpg',
                degree_documents=['degrees/demo_mbbs_degree.pdf'],
                latitude=DEMO_CITY_COORDS.get(loc.split(',')[-1].strip(), (31.5204, 74.3587))[0], # DEMO COORD
                longitude=DEMO_CITY_COORDS.get(loc.split(',')[-1].strip(), (31.5204, 74.3587))[1] # DEMO COORD
            )
            db.session.add(doc)
            db.session.commit()
            print(f"  + Created Doctor Profile: {name} ({category})")
        else:
            doc.category = category
            doc.specialization = spec
            doc.experience = float(exp)
            doc.pmc_code = pmc
            doc.education = edu
            doc.city = loc.split(',')[-1].strip()
            doc.location = loc
            doc.is_approved = True
            doc.is_verified = True
            doc.profile_completed = True
            doc.time_slots = weekly_slots
            doc.degree_documents = ['degrees/demo_mbbs_degree.pdf']
            city_key = loc.split(',')[-1].strip()
            doc.latitude, doc.longitude = DEMO_CITY_COORDS.get(city_key, (31.5204, 74.3587)) # DEMO COORD
            db.session.commit()
            print(f"  * Updated Doctor Profile: {name} ({category})")

        doctor_models.append(doc)

    # ── 3. 6 Demo Patients ─────────────────────────────────────────────────────
    print("\n3. Seeding 6 Demo Patients...")
    patients_spec = [
        ("Ahmed Raza", "patient.ahmed@example.com", "+92-300-2000001", "35201-2000001-1", "A+", "Penicillin", "Mild hypertension", "+92-300-9000001", "Brother", "AR", "#0ea5e9", date(1990, 5, 14), "male"),
        ("Mariam Khan", "patient.mariam@example.com", "+92-300-2000002", "35201-2000002-1", "B+", "None", "Seasonal allergies", "+92-300-9000002", "Spouse", "MK", "#ec4899", date(1994, 8, 22), "female"),
        ("Omar Sheikh", "patient.omar@example.com", "+92-300-2000003", "35201-2000003-1", "O+", "Peanuts", "None", "+92-300-9000003", "Father", "OS", "#f59e0b", date(1988, 11, 3), "male"),
        ("Sidra Amin", "patient.sidra@example.com", "+92-300-2000004", "35201-2000004-1", "AB+", "Dust / Pollen", "Migraines", "+92-300-9000004", "Mother", "SA", "#8b5cf6", date(1996, 2, 18), "female"),
        ("Bilal Hassan", "patient.bilal@example.com", "+92-300-2000005", "35201-2000005-1", "O-", "Sulfa drugs", "Asthma", "+92-300-9000005", "Sister", "BH", "#10b981", date(1993, 7, 9), "male"),
        ("Rabia Tahir", "patient.rabia@example.com", "+92-300-2000006", "35201-2000006-1", "A-", "None", "None", "+92-300-9000006", "Spouse", "RT", "#6366f1", date(1995, 10, 30), "female"),
    ]

    patient_models = []
    for (name, email, phone, cnic, blood, allergies, history, emerg_phone, emerg_rel, glyph, color, dob, gender) in patients_spec:
        user = get_or_create_user(
            name=name, email=email, phone=phone, cnic=cnic, role="patient",
            password="Patient2026!Demo#", avatar_text=glyph, bg_color=color
        )
        user.date_of_birth = dob
        user.gender = gender
        db.session.commit()

        patient = Patient.query.filter_by(user_id=user.id).first()
        if not patient:
            patient = Patient(
                user_id=user.id,
                blood_group=blood,
                allergies=allergies,
                medical_history=history,
                emergency_contact=emerg_phone,
                emergency_relation=emerg_rel,
                cnic_front_image='cnic/demo_patient_cnic.jpg',
                cnic_back_image='cnic/demo_patient_cnic.jpg'
            )
            db.session.add(patient)
            db.session.commit()
            print(f"  + Created Patient Profile: {name} (Complete: {patient.is_profile_complete()})")
        else:
            patient.blood_group = blood
            patient.allergies = allergies
            patient.medical_history = history
            patient.emergency_contact = emerg_phone
            patient.emergency_relation = emerg_rel
            db.session.commit()
            print(f"  * Updated Patient Profile: {name} (Complete: {patient.is_profile_complete()})")

        patient_models.append(patient)

    # ── 4. Medical Documents for Patients ─────────────────────────────────────
    print("\n4. Seeding Patient Clinical Documents...")
    sample_docs_spec = [
        # (patient_idx, filename, file_type, content, file_size)
        (0, 'complete_blood_count.pdf', 'pdf', b'%PDF-1.4 CBC_LAB_REPORT_NORMAL\n%%EOF', 2048),
        (0, 'chest_xray_report.png', 'png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa74d\x01\x00\x00\x00\x00IEND\xaeB`\x82', 1536),
        (1, 'lipid_panel_fasting.pdf', 'pdf', b'%PDF-1.4 LIPID_PROFILE_FASTING_NORMAL\n%%EOF', 2400),
        (1, 'thyroid_ultrasound.png', 'png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa74d\x01\x00\x00\x00\x00IEND\xaeB`\x82', 1820),
        (2, 'hba1c_glucose_report.pdf', 'pdf', b'%PDF-1.4 HBA1C_GLUCOSE_CONTROL_GOOD\n%%EOF', 1980),
    ]

    for (p_idx, fname, ftype, content, fsize) in sample_docs_spec:
        pat = patient_models[p_idx]
        pat_dir = os.path.join(priv_base, 'medical_documents', str(pat.id))
        os.makedirs(pat_dir, exist_ok=True)
        disk_path = os.path.join(pat_dir, fname)
        _write_file_if_missing(disk_path, content)

        existing_doc = MedicalDocument.query.filter_by(patient_id=pat.id, filename=fname).first()
        if not existing_doc:
            doc = MedicalDocument(
                patient_id=pat.id,
                filename=fname,
                file_path=f'medical_documents/{pat.id}/{fname}',
                file_type=ftype,
                file_size=fsize,
                is_visible_to_doctor=True
            )
            db.session.add(doc)
            db.session.commit()
            print(f"  + Added MedicalDocument '{fname}' for {pat.user.name}")
        else:
            print(f"  * MedicalDocument '{fname}' already exists for {pat.user.name}")

    # ── 5. Appointments in Different States ────────────────────────────────────
    print("\n5. Seeding Demo Appointments across Varied Workflow States...")
    tomorrow = date.today() + timedelta(days=1)
    yesterday = date.today() - timedelta(days=1)

    # Appt 1: Upcoming Approved Video Appointment (Ahmed with Dr. Tariq)
    appt1 = Appointment.query.filter_by(patient_id=patient_models[0].id, doctor_id=doctor_models[0].id).first()
    if not appt1:
        appt1 = Appointment(
            patient_id=patient_models[0].id,
            doctor_id=doctor_models[0].id,
            appointment_date=tomorrow,
            appointment_time=time(10, 0),
            duration=30,
            appointment_type='video',
            hospital='Doctors Hospital',
            status='approved',
            charges=2000.0,
            disease_category='Cardiology',
            symptoms='Routine cardiac checkup and lipid review',
            payment_status='approved',
            payment_submitted_at=datetime.utcnow() - timedelta(hours=2),
            payment_approved_at=datetime.utcnow() - timedelta(hours=1),
            approved_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(appt1)
        db.session.commit()
        print("  + Appt 1: Upcoming Approved Video Appointment (Ahmed -> Dr. Tariq)")
    else:
        appt1.status = 'approved'
        appt1.payment_status = 'approved'
        appt1.cancellation_requested = False
        appt1.cancellation_approved = False
        db.session.commit()
        print("  * Reset Appt 1: Status restored to 'approved' (Ahmed -> Dr. Tariq)")

    # Appt 2: Completed Appointment with Prescription (Mariam with Dr. Fatima)
    appt2 = Appointment.query.filter_by(patient_id=patient_models[1].id, doctor_id=doctor_models[3].id).first()
    if not appt2:
        appt2 = Appointment(
            patient_id=patient_models[1].id,
            doctor_id=doctor_models[3].id,
            appointment_date=yesterday,
            appointment_time=time(16, 0),
            duration=30,
            appointment_type='video',
            hospital='Aga Khan University Hospital',
            status='completed',
            charges=1800.0,
            disease_category='Dermatology',
            symptoms='Eczema flare-up on hands',
            payment_status='paid',
            prescription_unlocked=True,
            completed_at=datetime.utcnow() - timedelta(hours=20)
        )
        db.session.add(appt2)
        db.session.commit()

        rx = Prescription(
            appointment_id=appt2.id,
            diagnosis='Atopic dermatitis (eczema) with mild secondary irritation',
            advice='Apply topical corticosteroid ointment twice daily for 7 days. Use gentle ceramide moisturizer.',
            pdf_path='prescriptions/demo_prescription.pdf'
        )
        db.session.add(rx)
        db.session.commit()
        print("  + Appt 2: Completed Appointment with Prescription (Mariam -> Dr. Fatima)")
    elif appt2 and not appt2.prescription:
        rx = Prescription(
            appointment_id=appt2.id,
            diagnosis='Atopic dermatitis (eczema) with mild secondary irritation',
            advice='Apply topical corticosteroid ointment twice daily for 7 days. Use gentle ceramide moisturizer.',
            pdf_path='prescriptions/demo_prescription.pdf'
        )
        db.session.add(rx)
        db.session.commit()
        print("  + Appt 2: Attached Missing Prescription (Mariam -> Dr. Fatima)")

    # Appt 3: Manual Payment Screenshot Awaiting Admin Approval (Omar with Dr. Bilal)
    appt3 = Appointment.query.filter_by(patient_id=patient_models[2].id, doctor_id=doctor_models[2].id).first()
    if not appt3:
        appt3 = Appointment(
            patient_id=patient_models[2].id,
            doctor_id=doctor_models[2].id,
            appointment_date=tomorrow,
            appointment_time=time(11, 30),
            duration=30,
            appointment_type='video',
            hospital="Children's Hospital",
            status='pending',
            charges=1500.0,
            disease_category='Pediatrics',
            symptoms='Child persistent cough and fever',
            payment_status='submitted',
            payment_screenshot='payment_screenshots/demo_payment_slip.png',
            payment_submitted_at=datetime.utcnow() - timedelta(minutes=45)
        )
        db.session.add(appt3)
        db.session.commit()
        print("  + Appt 3: Payment Screenshot Awaiting Review (Omar -> Dr. Bilal)")
    else:
        appt3.status = 'pending'
        appt3.payment_status = 'submitted'
        appt3.payment_screenshot = 'payment_screenshots/demo_payment_slip.png'
        db.session.commit()
        print("  * Reset Appt 3: Status restored to 'submitted' (Omar -> Dr. Bilal)")

    # Appt 4: Pending Payment Appointment (Sidra with Dr. Zainab)
    appt4 = Appointment.query.filter_by(patient_id=patient_models[3].id, doctor_id=doctor_models[4].id).first()
    if not appt4:
        appt4 = Appointment(
            patient_id=patient_models[3].id,
            doctor_id=doctor_models[4].id,
            appointment_date=tomorrow,
            appointment_time=time(14, 0),
            duration=30,
            appointment_type='video',
            hospital='Lady Reading Hospital',
            status='pending',
            charges=2000.0,
            disease_category='Gynecology',
            symptoms='Pre-natal routine wellness consultation',
            payment_status='pending'
        )
        db.session.add(appt4)
        db.session.commit()
        print("  + Appt 4: Pending Payment Appointment (Sidra -> Dr. Zainab)")
    else:
        appt4.status = 'pending'
        appt4.payment_status = 'pending'
        appt4.payment_screenshot = None
        db.session.commit()
        print("  * Reset Appt 4: Status restored to 'pending' (Sidra -> Dr. Zainab)")

    # Appt 5: Completed with 5-Star Review (Bilal with Dr. Rashid)
    appt5 = Appointment.query.filter_by(patient_id=patient_models[4].id, doctor_id=doctor_models[11].id).first()
    if not appt5:
        appt5 = Appointment(
            patient_id=patient_models[4].id,
            doctor_id=doctor_models[11].id,
            appointment_date=yesterday,
            appointment_time=time(11, 0),
            duration=30,
            appointment_type='physical',
            hospital='Mayo Hospital',
            status='completed',
            charges=1500.0,
            disease_category='General Medicine',
            symptoms='Seasonal flu and body aches',
            payment_status='paid',
            completed_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(appt5)
        db.session.commit()

        rev = Review(
            appointment_id=appt5.id,
            doctor_id=doctor_models[11].id,
            patient_id=patient_models[4].id,
            rating=5,
            comment="Dr. Rashid Latif was extremely attentive and gave clear advice. Feeling much better now!",
            is_visible=True,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(rev)
        db.session.commit()
        print("  + Appt 5: Completed with Review (Bilal -> Dr. Rashid)")
    elif appt5 and not Review.query.filter_by(appointment_id=appt5.id).first():
        rev = Review(
            appointment_id=appt5.id,
            doctor_id=doctor_models[11].id,
            patient_id=patient_models[4].id,
            rating=5,
            comment="Dr. Rashid Latif was extremely attentive and gave clear advice. Feeling much better now!",
            is_visible=True,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(rev)
        db.session.commit()
        print("  + Appt 5: Attached Missing Review (Bilal -> Dr. Rashid)")

    # Appt 6: Cancelled with Processed Refund & Transfer Proof (Rabia with Dr. Hamza)
    appt6 = Appointment.query.filter_by(patient_id=patient_models[5].id, doctor_id=doctor_models[5].id).first()
    if not appt6:
        appt6 = Appointment(
            patient_id=patient_models[5].id,
            doctor_id=doctor_models[5].id,
            appointment_date=yesterday,
            appointment_time=time(12, 0),
            duration=30,
            appointment_type='video',
            hospital='Ghurki Trust Teaching Hospital',
            status='cancelled',
            charges=1700.0,
            disease_category='Orthopedics',
            symptoms='Knee sprain recovery',
            payment_status='paid',
            cancellation_requested=True,
            cancellation_approved=True,
            cancellation_reason='Emergency schedule conflict'
        )
        db.session.add(appt6)
        db.session.commit()

        ref = Refund(
            appointment_id=appt6.id,
            patient_id=patient_models[5].id,
            amount=1700.0,
            reason='patient_cancelled',
            status='completed',
            processed_at=datetime.utcnow() - timedelta(hours=5),
            admin_notes='Refund processed via Easypaisa transfer'
        )
        db.session.add(ref)
        db.session.commit()

        payout = RefundPayoutDetail(
            refund_id=ref.id,
            payment_method='easypaisa',
            account_title='Rabia Tahir',
            account_number='03002000006',
            admin_proof_path='refund_proofs/demo_refund_receipt.png',
            admin_proof_note='Transferred from Quick Care operations account',
            submitted_at=datetime.utcnow() - timedelta(hours=6)
        )
        db.session.add(payout)
        db.session.commit()
        print("  + Appt 6: Cancelled with Processed Refund Proof (Rabia -> Dr. Hamza)")
    elif appt6 and not Refund.query.filter_by(appointment_id=appt6.id).first():
        ref = Refund(
            appointment_id=appt6.id,
            patient_id=patient_models[5].id,
            amount=1700.0,
            reason='patient_cancelled',
            status='completed',
            processed_at=datetime.utcnow() - timedelta(hours=5),
            admin_notes='Refund processed via Easypaisa transfer'
        )
        db.session.add(ref)
        db.session.commit()

        payout = RefundPayoutDetail(
            refund_id=ref.id,
            payment_method='easypaisa',
            account_title='Rabia Tahir',
            account_number='03002000006',
            admin_proof_path='refund_proofs/demo_refund_receipt.png',
            admin_proof_note='Transferred from Quick Care operations account',
            submitted_at=datetime.utcnow() - timedelta(hours=6)
        )
        db.session.add(payout)
        db.session.commit()
        print("  + Appt 6: Attached Missing Refund (Rabia -> Dr. Hamza)")

    # ── 6. Execute Multi-Tenant Data Migration & Hierarchy Seeding ──────────────
    print("\n[TENANT MIGRATION] Executing multi-tenant hospital migration and hierarchy seed...")
    try:
        from scripts.migrate_tenant_data import run_data_migration
        run_data_migration()
    except Exception as e:
        print(f"[TENANT MIGRATION] Warning: {e}")

    # ── 7. Write Comprehensive Aramis Health DEMO_CREDENTIALS.md ─────────────────
    creds_path = os.path.join(app.instance_path, 'DEMO_CREDENTIALS.md')
    with open(creds_path, 'w', encoding='utf-8') as f:
        f.write("# Aramis AI Healthcare Solutions — Demo Credentials\n\n")
        f.write("*Confidential — Multi-tenant evaluation and verification only.*\n\n")
        
        f.write("## 1. Global Platform Super Admin\n\n")
        f.write("| Level | Role | Name | Email | Password | Privileges |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        f.write("| 0 | Platform Super Admin | Global Super Admin | `superadmin@example.com` | `Aramis2026!Demo#` | Global Supervision, BYPASSRLS Engine, Hospital Onboarding |\n\n")

        f.write("## 2. Hospital 1: Aramis Demo Hospital (Lahore)\n\n")
        f.write("| Level | Hierarchy Role | Name | Email | Password | Scope & Responsibilities |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        f.write("| 1 | Hospital Admin | Dr. Farooq Qureshi | `admin.demo@aramis.health` | `Aramis2026!Demo#` | Hospital Tenant Executive, Org Chart, Staff Promotion |\n")
        f.write("| 2 | Medical Director | Dr. Naveed Akhtar | `director.demo@aramis.health` | `Aramis2026!Demo#` | Clinical Leadership, HOD Oversight, Clinical Quality |\n")
        f.write("| 2 | Operations Manager | Salman Tariq | `ops.demo@aramis.health` | `Aramis2026!Demo#` | Facility Operations, Front Desk & OT Coordination |\n")
        f.write("| 2 | Finance Manager | Zubair Hassan | `finance.demo@aramis.health` | `Aramis2026!Demo#` | Financial Reconciliation & Payouts (Zero Clinical Payload) |\n")
        f.write("| 2 | HR / IT Manager | Sadia Malik | `hr.demo@aramis.health` | `Aramis2026!Demo#` | Staff Compliance, IT System Access |\n")
        f.write("| 3 | HOD Cardiology | Dr. Tariq Mahmood | `dr.tariq@example.com` | `Doctor2026!Demo#` | Cardiology Department Head, Attending Cardiologist |\n")
        f.write("| 4 | Clinical Nurse | Nurse Ayesha Bibi | `nurse.demo@aramis.health` | `Aramis2026!Demo#` | Inpatient & OPD Care, Vitals Monitoring |\n")
        f.write("| 4 | OT Coordinator | Kamran Aslam | `ot.demo@aramis.health` | `Aramis2026!Demo#` | Operation Theater Scheduling |\n")
        f.write("| 4 | Front Desk | Fatima Noor | `frontdesk.demo@aramis.health` | `Aramis2026!Demo#` | Patient Check-in & In-person Reception |\n")
        f.write("| 4 | Hospital Accountant | Imran Javed | `accountant.demo@aramis.health` | `Aramis2026!Demo#` | Invoice & Payment Processing (Zero Clinical Payload) |\n")
        f.write("| 4 | Staff Compliance | Bilal Mehmood | `compliance.demo@aramis.health` | `Aramis2026!Demo#` | PMC Accreditation Verification |\n\n")

        f.write("## 3. Hospital 2: Aramis City Clinic (Islamabad)\n\n")
        f.write("| Level | Hierarchy Role | Name | Email | Password | Scope & Responsibilities |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        f.write("| 1 | Hospital Admin | Dr. Arshad Beg | `admin.city@aramis.health` | `Aramis2026!Demo#` | Islamabad Executive, Facility Supervision |\n")
        f.write("| 2 | Medical Director | Dr. Shireen Khan | `director.city@aramis.health` | `Aramis2026!Demo#` | Clinical Governance |\n")
        f.write("| 2 | Operations Manager | Taimoor Shah | `ops.city@aramis.health` | `Aramis2026!Demo#` | Islamabad Branch Operations |\n")
        f.write("| 2 | Finance Manager | Fahad Riaz | `finance.city@aramis.health` | `Aramis2026!Demo#` | Islamabad Branch Accounting |\n")
        f.write("| 2 | HR / IT Manager | Nida Parveen | `hr.city@aramis.health` | `Aramis2026!Demo#` | HR Administration |\n")
        f.write("| 3 | HOD Cardiology | Dr. Haroon Rasheed | `hod.cardio.city@aramis.health` | `Aramis2026!Demo#` | Cardiology Department Head |\n")
        f.write("| 4 | Attending Cardiologist | Dr. Usman Ali | `dr.usman@aramis.health` | `Aramis2026!Demo#` | Clinical Cardiology Consultations |\n")
        f.write("| 4 | Clinical Nurse | Nurse Zainab Bibi | `nurse.city@aramis.health` | `Aramis2026!Demo#` | Patient Care & Vitals |\n")
        f.write("| 4 | OT Coordinator | Rehan Siddique | `ot.city@aramis.health` | `Aramis2026!Demo#` | Clinical Scheduling |\n")
        f.write("| 4 | Front Desk | Saima Gul | `frontdesk.city@aramis.health` | `Aramis2026!Demo#` | Executive OPD Reception |\n")
        f.write("| 4 | Hospital Accountant | Kashif Raza | `accountant.city@aramis.health` | `Aramis2026!Demo#` | Fee Verification |\n")
        f.write("| 4 | Staff Compliance | Yasmeen Akhtar | `compliance.city@aramis.health` | `Aramis2026!Demo#` | Compliance Audit |\n\n")

        f.write("## 4. Global Patients\n\n")
        f.write("| Name | Email | Password | Cross-Hospital Records |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write("| Ahmed Raza | `patient.ahmed@example.com` | `Patient2026!Demo#` | Consulted at both Hospital 1 (Lahore) and Hospital 2 (Islamabad) |\n")
        f.write("| Fatima Ali | `patient.fatima@example.com` | `Patient2026!Demo#` | Hospital 1 Consultations |\n")

    print(f"\n[DEMO SEED COMPLETED SUCCESSFULLY]")
    print(f"Credentials written to: {creds_path}")


if __name__ == '__main__':
    from app import create_app
    app = create_app('development')
    with app.app_context():
        seed_demo_data(app)
