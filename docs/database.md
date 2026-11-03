# Database: schema and class diagram

PostgreSQL 17 (Docker, `compose.yaml`), normalised to third normal form, managed by Alembic migrations
(`backend/migrations`, currently at revision `0005`, operating theatres). Each backend module owns its tables
in its own `models.py`; `backend/app/models.py` registers them all. Design decisions are in the sections below.

## Tables by module

| Module | Tables |
|---|---|
| core | `audit_log` |
| auth | `users` |
| organization | `departments` |
| staff | `staff_members` |
| patients | `patients` |
| scheduling | `doctor_schedules`, `schedule_days`, `schedule_breaks`, `hospital_closures` |
| appointments | `appointments` |
| reception (voice) | `voice_calls`, `voice_call_bookings` |
| scribe | `encounters`, `encounter_codes`, `encounter_tasks` |
| clinical | `lab_tests`, `lab_results`, `vital_signs`, `clinical_reports`, `clinical_history`, `patient_allergies` |
| theatre | `theatres`, `procedures`, `surgical_cases`, `preop_assessments`, `theatre_rosters`, `staff_leave` |

## Entity–relationship diagram (tables)

PK = primary key, FK = foreign key, UK = unique.

```mermaid
erDiagram
    users {
        varchar username PK
        varchar display_name
        varchar role "admin | doctor | nurse | receptionist | patient"
        varchar password_hash "scrypt"
        boolean active
        int session_version "bumped to end all sessions"
        bigint patient_id FK,UK "patient accounts only"
        timestamptz created_at
    }
    departments {
        int id PK
        varchar code UK "e.g. CARD"
        varchar name UK
        varchar kind "clinical | diagnostic | support | administrative"
        boolean active
        timestamptz created_at
    }
    staff_members {
        int id PK
        varchar username FK,UK
        int department_id FK
        varchar job_title
        varchar specialty
        varchar registration_number UK
        boolean bookable "takes OPD appointments"
        timestamptz created_at
    }
    patients {
        bigint id PK
        varchar mrn UK "nullable"
        varchar full_name
        varchar sex "Female | Male | Other | Not stated"
        date date_of_birth
        varchar phone
        varchar email
        boolean registered "permanent record"
        timestamptz created_at
    }
    doctor_schedules {
        int id PK
        int staff_id FK,UK
        smallint slot_minutes "5 to 120"
        varchar updated_by FK
        timestamptz updated_at
    }
    schedule_days {
        int schedule_id PK,FK
        smallint weekday PK "0 = Monday"
        boolean enabled
        time opens
        time closes
    }
    schedule_breaks {
        int schedule_id PK,FK
        smallint weekday PK,FK
        time starts PK
        time ends
    }
    hospital_closures {
        date closed_on PK
        varchar reason
    }
    appointments {
        int id PK
        bigint patient_id FK
        int practitioner_id FK "the doctor"
        varchar reason
        timestamptz start_time "unique per doctor while active"
        boolean canceled
        varchar booked_via "voice | desk | portal"
        timestamptz created_at
    }
    voice_calls {
        varchar id PK "VAPI call id"
        timestamptz started_at
        timestamptz ended_at
        text transcript "stored once per call"
        timestamptz created_at
    }
    voice_call_bookings {
        varchar call_id PK,FK
        int appointment_id PK,FK,UK
    }
    encounters {
        varchar id PK "uuid hex"
        varchar username FK "the doctor"
        bigint patient_id FK "SET NULL on purge"
        varchar source "live | recording | sample"
        jsonb transcript "document"
        varchar visit_type
        varchar note_status "drafting | ready | failed"
        jsonb draft_note "document"
        jsonb final_note "document"
        timestamptz approved_at
        varchar codes_source "draft | signed"
        varchar tasks_source "draft | signed"
        int lines_drafted_kept_added_removed "4 metric columns"
        timestamptz content_purged_at
        timestamptz created_at
    }
    encounter_codes {
        varchar encounter_id PK,FK
        smallint position PK
        varchar code "ICD-10"
        varchar kind
        varchar confidence
        text evidence
    }
    encounter_tasks {
        varchar encounter_id PK,FK
        smallint position PK
        text title
        varchar category
        varchar owner
        boolean done
    }
    audit_log {
        bigint id PK
        timestamptz ts
        varchar username "no FK: failed sign-ins log unknown names"
        varchar action
        varchar encounter_id FK
        jsonb detail "ids and counts only"
    }

    departments ||--o{ staff_members : "employs"
    users ||--o| staff_members : "staff profile"
    patients ||--o| users : "portal account"
    staff_members ||--o| doctor_schedules : "OPD week"
    doctor_schedules ||--o{ schedule_days : "days"
    schedule_days ||--o{ schedule_breaks : "breaks"
    users |o--o{ doctor_schedules : "last edited"
    patients ||--o{ appointments : "booked for"
    staff_members ||--o{ appointments : "with doctor"
    voice_calls ||--o{ voice_call_bookings : "booked in call"
    appointments ||--o| voice_call_bookings : "voice booking"
    users ||--o{ encounters : "records"
    patients |o--o{ encounters : "seen in"
    encounters ||--o{ encounter_codes : "code list"
    encounters ||--o{ encounter_tasks : "task checklist"
    encounters |o--o{ audit_log : "audited in"
```

### Clinical data and operating theatres (migrations 0004, 0005)

Models: `backend/app/modules/clinical/models.py`, `backend/app/modules/theatre/models.py`. Clinical rows are
deleted with their patient; a theatre case is not (it is cancelled instead). Lab flags are computed when a result
is stored; vital-sign reference ranges are constants (`clinical/service.py`, `VITAL_RANGES`), not rows.

| Table | Key | Columns |
|---|---|---|
| lab_tests | id | code (HGB, WBC, PLT, NA, K, CREA, GLU, ALB, INR; seeded by the migration), name, unit, ref_low, ref_high, category |
| lab_results | id | patient, test, value, flag, collected_at, source (seed/manual/import), entered_by |
| vital_signs | id | patient, recorded_at, heart_rate, systolic/diastolic BP, spo2, temperature_c, resp_rate (each nullable) |
| clinical_reports | id | patient, kind (ultrasound, ECG, X-ray, CT, MRI, echo, …), title, reported_on, body, author |
| clinical_history | id | patient, kind (indication/condition/surgery), noted_on, text |
| patient_allergies | id | patient, substance, reaction, severity |
| theatres | id | code ("OR 1"), name, department, specialty, cleaning_minutes |
| procedures | code (OPS) | title, specialty, minutes per phase (induction, lead-in, incision, lead-out, emergence), variance, risk model (VitalDB / EuroSCORE II), source of the duration |
| surgical_cases | id | patient, procedure, theatre, scheduled_on (NULL = waiting list), seq, urgency, surgeon, overrun_minutes, deferred, canceled |
| preop_assessments | case | ASA, weight, height, EuroSCORE II inputs (LVEF, NYHA, PA pressure, risk flags) |
| theatre_rosters | (staff, weekday) | session start and end |
| staff_leave | id | staff, starts_on, ends_on, reason |

The demo seed (`python -m app seed demo-theatre`) converts the theatre POC's data: its surgeons become doctor accounts
with staff profiles, rosters and leave; its patients become registered patients (MRN `DEMO-Pxx`) with their
labs, vitals (one row per day), history, reports and allergies; its dates are replayed on the current week.

```mermaid
erDiagram
    patients ||--o{ lab_results : "results"
    lab_tests ||--o{ lab_results : "of test"
    patients ||--o{ vital_signs : "observations"
    patients ||--o{ clinical_reports : "reports"
    patients ||--o{ clinical_history : "history"
    patients ||--o{ patient_allergies : "allergies"
    departments ||--o{ theatres : "runs"
    patients ||--o{ surgical_cases : "operated on"
    procedures ||--o{ surgical_cases : "operation"
    theatres ||--o{ surgical_cases : "listed in"
    staff_members |o--o{ surgical_cases : "surgeon"
    surgical_cases ||--o| preop_assessments : "pre-op"
    staff_members ||--o{ theatre_rosters : "theatre week"
    staff_members ||--o{ staff_leave : "leave"
```

## Class diagram (SQLAlchemy models, by module)

Arrows are relationships the code navigates; `*--` means the parts are owned and deleted with the whole.

```mermaid
classDiagram
    direction LR

    namespace core {
        class AuditLog {
            +int id
            +datetime ts
            +str username
            +str action
            +str encounter_id
            +dict detail
        }
    }
    namespace auth {
        class User {
            +str username
            +str display_name
            +str role
            +bool active
            +int session_version
            +Patient patient
        }
    }
    namespace organization {
        class Department {
            +int id
            +str code
            +str name
            +str kind
            +bool active
        }
    }
    namespace staff {
        class StaffMember {
            +int id
            +User account
            +Department department
            +str job_title
            +str specialty
            +str registration_number
            +bool bookable
            +display_name() str
        }
    }
    namespace patients {
        class Patient {
            +int id
            +str mrn
            +str full_name
            +str sex
            +date date_of_birth
            +str phone
            +str email
            +bool registered
        }
    }
    namespace scheduling {
        class DoctorSchedule {
            +int id
            +int staff_id
            +int slot_minutes
            +list~ScheduleDay~ days
        }
        class ScheduleDay {
            +int weekday
            +bool enabled
            +time opens
            +time closes
            +list~ScheduleBreak~ breaks
        }
        class ScheduleBreak {
            +time starts
            +time ends
        }
        class HospitalClosure {
            +date closed_on
            +str reason
        }
    }
    namespace appointments {
        class Appointment {
            +int id
            +Patient patient
            +StaffMember practitioner
            +str reason
            +datetime start_time
            +bool canceled
            +str booked_via
            +patient_name() str
        }
    }
    namespace reception {
        class VoiceCall {
            +str id
            +datetime started_at
            +datetime ended_at
            +str transcript
        }
        class VoiceCallBooking {
            +str call_id
            +int appointment_id
        }
    }
    namespace scribe {
        class Encounter {
            +str id
            +str username
            +Patient patient
            +dict transcript
            +dict draft_note
            +dict final_note
            +datetime approved_at
            +list~EncounterCode~ codes
            +list~EncounterTask~ tasks
        }
        class EncounterCode {
            +int position
            +str code
            +str kind
            +str confidence
        }
        class EncounterTask {
            +int position
            +str title
            +str category
            +bool done
        }
    }

    User "0..1" --> "0..1" Patient : patient
    StaffMember "0..1" --> "1" User : account
    StaffMember "*" --> "1" Department : department
    DoctorSchedule "0..1" --> "1" StaffMember : staff_id
    DoctorSchedule "1" *-- "*" ScheduleDay : days
    ScheduleDay "1" *-- "*" ScheduleBreak : breaks
    Appointment "*" --> "1" Patient : patient
    Appointment "*" --> "1" StaffMember : practitioner
    VoiceCallBooking "*" --> "1" VoiceCall : call_id
    VoiceCallBooking "0..1" --> "1" Appointment : appointment_id
    Encounter "*" --> "1" User : username
    Encounter "*" --> "0..1" Patient : patient
    Encounter "1" *-- "*" EncounterCode : codes
    Encounter "1" *-- "*" EncounterTask : tasks
    AuditLog "*" --> "0..1" Encounter : encounter_id
```

## Constraints the database enforces

| Table | Rule |
|---|---|
| users | role in the five roles; `(role = 'patient') = (patient_id IS NOT NULL)`; one account per patient |
| departments | code (`^[A-Z0-9_-]{2,16}$`) and name unique; kind in its list |
| staff_members | one profile per account; registration number unique |
| patients | MRN unique; name not blank; sex in its list |
| appointments | **one active appointment per doctor per start time** (partial unique index); `booked_via` in its list |
| voice_call_bookings | an appointment belongs to at most one call |
| doctor_schedules | one per doctor; slot 5–120 minutes |
| schedule_days / breaks | weekday 0–6; an open day closes after it opens; a break ends after it starts |
| encounters, codes, tasks | statuses and enumerations in their lists; codes and tasks deleted with their encounter |
| lab_tests / lab_results | test code unique; `ref_low < ref_high`; flag in low/normal/high |
| vital_signs | each measurement nullable but within physiological bounds (e.g. SpO2 50–100) |
| clinical_reports / history / allergies | kind and severity in their lists |
| surgical_cases | urgency in the four NCEPOD categories; `overrun_minutes >= 0`; waiting list = `scheduled_on IS NULL` |
| preop_assessments | one per case; ASA 1–6, LVEF 5–90, NYHA 1–4 |
| theatre_rosters / staff_leave | one roster row per surgeon per weekday, start before end; leave ends on or after it starts |

## Why it is in 3NF

- **One fact, one place.** Patient demographics live only in `patients`; a call transcript only in `voice_calls`;
  a staff member's department only in `staff_members`.
- **Derived, not stored.** An appointment's department is its doctor's department, so `appointments` has no
  `department_id`.
- **Link facts are their own rows.** "This appointment was booked in that call" is `voice_call_bookings`, owned by
  the voice module, so `appointments` does not depend on any booking channel.
- **No repeating groups.** Weeks, breaks, closed dates, code lists and task checklists are rows.
- **Deliberate documents.** `transcript`, `draft_note`, `final_note` (written and read whole, cited by segment id)
  and `audit_log.detail` (free-form metadata) are JSONB.

## Retention

After `RETENTION_DAYS` the purge clears an encounter's transcript, notes, code and task rows and its patient link
(metrics columns stay). A **provisional** patient row (created by the scribe form or a phone booking, not
registered) is deleted once nothing references it. Registered patients are permanent hospital records.

## Adding a hospital module's tables

Create `app/modules/<name>/models.py`, import its classes in `backend/app/models.py`, run
`alembic revision --autogenerate -m "add <name>"`, review the file (CHECK constraints and data moves are written by
hand), and run the tests: `test_migrations_match_the_models` fails if the migration and the models disagree.
