"""Who may do what. The single source of truth for authorization: routes declare the permission they need
(`require("scribe.use")`), and /api/me sends each user their permissions so the UI shows only what they may use.

To change what a role can see or do, edit ROLE_PERMISSIONS; nothing else hard-codes roles. A new hospital module
adds its permissions to `Permission` and grants them to roles here. A new role also needs a migration (the
`ck_users_role` CHECK constraint lists the roles).
"""

from typing import Literal

Role = Literal["admin", "doctor", "nurse", "receptionist", "patient"]
ROLES: tuple[Role, ...] = ("admin", "doctor", "nurse", "receptionist", "patient")
STAFF_ROLES: tuple[Role, ...] = ("admin", "doctor", "nurse", "receptionist")

Permission = Literal[
    # Overview and organisation
    "dashboard.view",  # staff overview page
    "organization.manage",  # create, rename, deactivate departments
    "staff.view",  # staff directory and departments
    "staff.manage",  # staff profiles: department, title, specialty, registration, bookable
    "users.manage",  # create, edit, disable accounts; reset passwords
    # Patients and OPD
    "patients.view",  # patient registry: search and read demographics
    "patients.manage",  # register patients, edit demographics
    "appointments.view",  # appointments board and call transcripts
    "appointments.book",  # book appointments at the front desk
    "appointments.manage",  # cancel appointments
    "schedule.view",  # doctors' OPD schedules and hospital closed dates
    "schedule.edit",
    # Clinical
    "scribe.use",  # record encounters, draft/review/sign notes, codes, tasks, letters, own metrics
    "clinical.view",  # a patient's labs, vitals, reports, history and allergies
    # Operating theatres
    "theatre.view",  # theatre board, lists, waiting list, calendar, case details
    "theatre.manage",  # book, move, defer and cancel cases; place emergencies
    "theatre.roster",  # surgeons' theatre sessions and leave
    "theatre.insights",  # model checks and the scheduling experiment
    # Front desk and oversight
    "voice_agent.use",  # test-call the VAPI voice agent from the browser
    "metrics.view_all",  # hospital-wide pilot metrics
    "call_costs.view",
    # Patients themselves
    "portal.use",  # a patient's own profile and appointments
]

_STAFF: frozenset[Permission] = frozenset(
    {"dashboard.view", "staff.view", "patients.view", "appointments.view", "schedule.view", "theatre.view"}
)
_NURSE = _STAFF | {"clinical.view"}
_DOCTOR = _STAFF | {
    "scribe.use",
    "appointments.manage",
    "voice_agent.use",
    "clinical.view",
    "theatre.manage",
    "theatre.insights",
}
_RECEPTIONIST = _STAFF | {"patients.manage", "appointments.book", "appointments.manage", "voice_agent.use"}
_ADMIN = (
    _DOCTOR
    | _RECEPTIONIST
    | {
        "organization.manage",
        "staff.manage",
        "users.manage",
        "schedule.edit",
        "theatre.roster",
        "metrics.view_all",
        "call_costs.view",
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    "admin": _ADMIN,
    "doctor": _DOCTOR,
    "nurse": _NURSE,
    "receptionist": _RECEPTIONIST,
    "patient": frozenset({"portal.use"}),
}


def permissions_for(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())  # type: ignore[arg-type]
