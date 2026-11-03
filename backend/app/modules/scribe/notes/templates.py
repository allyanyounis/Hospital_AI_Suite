from pydantic import BaseModel


class TemplateSection(BaseModel):
    heading: str
    guidance: str


class NoteTemplate(BaseModel):
    id: str
    name: str
    description: str
    sections: list[TemplateSection]


def _t(id: str, name: str, description: str, sections: list[tuple[str, str]]) -> NoteTemplate:
    return NoteTemplate(
        id=id,
        name=name,
        description=description,
        sections=[TemplateSection(heading=h, guidance=g) for h, g in sections],
    )


# Cardiology templates first; SOAP kept as a general fallback.
# Scores (NYHA, CHA2DS2-VASc, HAS-BLED, GRACE...) are recorded only when the clinician states them, never calculated.
TEMPLATES: dict[str, NoteTemplate] = {
    t.id: t
    for t in [
        _t(
            "cardiology-clinic",
            "Cardiology clinic follow-up",
            "General cardiology outpatient review.",
            [
                ("Reason for visit", "Condition being followed up and purpose of the visit."),
                (
                    "Symptoms",
                    "Chest pain, breathlessness, orthopnoea/PND, palpitations, syncope/presyncope, oedema, exercise tolerance; relevant negatives the patient explicitly denied.",
                ),
                (
                    "Cardiac history & procedures",
                    "Prior MI, PCI/CABG, devices, valve disease, arrhythmias, as mentioned.",
                ),
                (
                    "Medications",
                    "Current cardiac medicines with doses; antithrombotics listed explicitly; any changes made today.",
                ),
                ("Examination", "Vital signs and examination findings stated by the clinician."),
                (
                    "Investigations",
                    "ECG, echo (EF), Holter, bloods (lipids, renal function, potassium) and other results discussed.",
                ),
                ("Assessment", "Clinician's stated assessment, including functional class or scores only if stated."),
                (
                    "Plan",
                    "Medication changes, investigations, referrals, lifestyle advice, safety-netting, follow-up interval.",
                ),
            ],
        ),
        _t(
            "acs-admission",
            "Chest pain / ACS admission",
            "Emergency or admission note for suspected acute coronary syndrome.",
            [
                ("Presenting complaint", "One line: main symptom and duration."),
                (
                    "History of presenting illness",
                    "Onset, character, site, radiation, severity, associated symptoms, prior similar episodes, relevant negatives.",
                ),
                (
                    "Cardiac risk factors",
                    "Hypertension, diabetes, dyslipidaemia, smoking (amount), family history of premature CAD, known CAD.",
                ),
                (
                    "Past history, medications & allergies",
                    "Relevant history, current medicines, allergies including contrast allergy if mentioned.",
                ),
                ("Examination", "Vital signs and examination findings stated by the clinician."),
                ("ECG & investigations", "ECG findings, troponin, other bloods and imaging ordered or discussed."),
                ("Assessment", "Working diagnosis and differentials; risk scores only if stated."),
                (
                    "Plan & disposition",
                    "Treatment given (antiplatelets, anticoagulation, analgesia), monitoring, cardiology referral/cath lab decision, admission, safety-netting.",
                ),
            ],
        ),
        _t(
            "hf-clinic",
            "Heart failure clinic",
            "Heart failure review: congestion, functional class and guideline-directed therapy.",
            [
                ("Reason for visit", "Type of heart failure if stated (e.g. HFrEF) and purpose of the visit."),
                (
                    "Symptoms & functional class",
                    "Breathlessness and exercise tolerance, orthopnoea, PND, fatigue, dizziness; NYHA class only if stated.",
                ),
                ("Fluid status", "Daily weights and trend, oedema, diet/fluid/salt intake, triggers mentioned."),
                (
                    "Heart failure medications",
                    "ARNI/ACEi/ARB, beta-blocker, MRA, SGLT2 inhibitor, diuretic: agent, dose, adherence, side effects.",
                ),
                ("Examination", "BP, HR, rhythm, SpO2, JVP, chest, oedema as stated."),
                (
                    "Results",
                    "Ejection fraction, potassium, creatinine/renal function, NT-proBNP and other results discussed.",
                ),
                ("Assessment", "Clinician's assessment of congestion, stability and functional class."),
                (
                    "Plan",
                    "Dose changes with new dose and duration, titration decisions and reasons, monitoring bloods, self-care advice (weights, fluid/salt), HF nurse contact, follow-up, return precautions.",
                ),
            ],
        ),
        _t(
            "af-review",
            "Atrial fibrillation review",
            "AF clinic: symptoms, stroke prevention, bleeding risk and rate/rhythm strategy.",
            [
                ("Reason for visit", "Type of AF if stated and purpose of the visit."),
                ("Symptoms", "Palpitation frequency and duration, breathlessness, chest pain, syncope."),
                (
                    "Stroke & bleeding risk",
                    "CHA2DS2-VASc / HAS-BLED only as stated by the clinician; bleeding symptoms reported.",
                ),
                (
                    "Anticoagulation",
                    "Agent, dose, frequency, adherence; dose-adjustment factors discussed (age, weight, renal function); interacting antiplatelets.",
                ),
                ("Rate / rhythm control", "Current strategy and medicines with doses."),
                (
                    "Examination & investigations",
                    "HR, rhythm, BP, weight, ECG, renal function and other results stated.",
                ),
                ("Assessment", "Clinician's stated assessment."),
                (
                    "Plan",
                    "Medication changes (including stopped medicines), monitoring bloods, letters to GP, follow-up, bleeding/stroke return precautions.",
                ),
            ],
        ),
        _t(
            "post-pci",
            "Post-PCI follow-up",
            "Clinic review after coronary stenting.",
            [
                (
                    "Index event & procedure",
                    "Presentation (e.g. NSTEMI/STEMI), vessel(s) treated, stent type and date or time since PCI, access site.",
                ),
                (
                    "Symptoms since discharge",
                    "Angina, breathlessness, bleeding, bruising, side effects, cardiac rehabilitation attendance.",
                ),
                (
                    "Antiplatelet therapy",
                    "Agents and doses, planned duration of dual antiplatelet therapy and end date, adherence, instructions about not stopping.",
                ),
                (
                    "Secondary prevention",
                    "Statin and lipid results vs target, other lipid therapy, BP, smoking status, beta-blocker/ACE inhibitor.",
                ),
                ("Examination", "Vital signs, access site and examination findings stated."),
                ("Investigations", "Echo EF, lipids, ECG and other results discussed."),
                ("Assessment", "Clinician's stated assessment."),
                (
                    "Plan",
                    "Medication changes, return to work/driving advice given, rehab, repeat bloods, follow-up, return precautions.",
                ),
            ],
        ),
        _t(
            "echo-report",
            "Echo report (dictation)",
            "Transthoracic echocardiogram report dictated by a single clinician.",
            [
                ("Indication", "Patient and clinical indication for the study; image quality and rhythm."),
                ("Left ventricle", "Size and dimensions, wall motion, EF with method, diastolic function."),
                ("Right ventricle", "Size and function, TAPSE."),
                ("Atria", "Left and right atrial size."),
                ("Valves", "Each valve: stenosis/regurgitation and severity as dictated."),
                ("Haemodynamics & other", "PASP, IVC, pericardium, aorta."),
                ("Conclusion", "The dictated conclusion and comparison with previous studies."),
            ],
        ),
        _t(
            "soap",
            "SOAP note",
            "General-purpose Subjective / Objective / Assessment / Plan note.",
            [
                (
                    "Subjective",
                    "Presenting complaint, history of presenting complaint, relevant symptoms and negatives, past history, medications, allergies, social history as reported by the patient.",
                ),
                ("Objective", "Examination findings, vital signs and test results that the clinician states aloud."),
                ("Assessment", "The clinician's stated impression, working diagnosis and differentials."),
                (
                    "Plan",
                    "Investigations, treatment, prescriptions, patient education, safety-netting and follow-up as stated.",
                ),
            ],
        ),
    ]
}
