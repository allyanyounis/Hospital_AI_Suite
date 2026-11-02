"""Synthetic, scripted cardiology consultations for demos and testing. No real patient data.

Speaker 0 is the clinician, speaker 1 the patient. The echo report is single-speaker dictation.
Timings are estimated from word count.
"""

from ..transcription import Segment, Transcript

_SCRIPTS: dict[str, tuple[str, list[tuple[int, str]]]] = {
    "ed-chest-pain": (
        "Emergency: chest pain, 54-year-old man",
        [
            (0, "Hi, I'm Dr. Rahman, one of the emergency doctors. What brings you in today?"),
            (
                1,
                "I've had this pain in my chest since about seven this morning. It came on while I was walking up the stairs at work.",
            ),
            (0, "Can you describe the pain for me? Where exactly is it?"),
            (
                1,
                "It's in the middle of my chest, like a heavy pressure. It goes into my left arm and a bit into my jaw.",
            ),
            (0, "On a scale of zero to ten, how bad is it?"),
            (1, "When it started it was about an eight. Now it's maybe a five."),
            (0, "Any shortness of breath, sweating, or feeling sick?"),
            (1, "I was sweaty and a bit short of breath at the start. No vomiting."),
            (0, "Have you ever had anything like this before?"),
            (
                1,
                "I've had some tightness when I walk fast over the last two weeks, but it always went away when I rested.",
            ),
            (0, "Do you have any medical problems? Blood pressure, diabetes, cholesterol?"),
            (1, "High blood pressure and high cholesterol. I take amlodipine five milligrams and atorvastatin twenty."),
            (0, "Any allergies to medications?"),
            (1, "Penicillin. I get a rash."),
            (0, "Do you smoke?"),
            (1, "About fifteen a day for thirty years. My father had a heart attack at fifty-eight."),
            (
                0,
                "Okay. Your blood pressure is one fifty-eight over ninety-four, heart rate ninety-six, oxygen ninety-seven percent on room air. Heart sounds are normal, chest is clear, no leg swelling.",
            ),
            (
                0,
                "I'm worried this could be your heart, so we'll treat it seriously. I'm going to get an ECG right now, bloods including troponin, and a chest X-ray.",
            ),
            (
                0,
                "I'll give you three hundred milligrams of aspirin to chew, and a spray under your tongue for the pain. We'll keep you on the monitor.",
            ),
            (0, "Depending on the ECG and troponin, I'll be speaking to the cardiology team about admitting you."),
            (1, "Okay. Should I call my wife?"),
            (
                0,
                "Yes, please do. If the pain gets worse or you feel faint at any point, press the call bell straight away.",
            ),
        ],
    ),
    "hf-clinic": (
        "Heart failure clinic: worsening breathlessness, 66-year-old man",
        [
            (0, "Good morning, Mr. Ahmed. How have you been since we saw you six weeks ago?"),
            (
                1,
                "Not so good this last week. I get breathless walking to the mosque, which is only about a hundred metres.",
            ),
            (0, "Are you able to lie flat at night?"),
            (
                1,
                "I've needed three pillows for the past few nights. Once I woke up gasping and had to sit on the edge of the bed.",
            ),
            (0, "Have you noticed any swelling? And are you weighing yourself every morning?"),
            (
                1,
                "My ankles are swollen by the evening. My weight has gone up from seventy-eight to eighty-one kilos this week.",
            ),
            (0, "Any chest pain, palpitations, or dizziness?"),
            (1, "No chest pain. No palpitations. A little dizzy when I stand up quickly."),
            (0, "Let's go through your tablets. What are you taking at the moment?"),
            (
                1,
                "The sacubitril valsartan, forty-nine fifty-one, twice a day. Bisoprolol five milligrams. Spironolactone twenty-five. Dapagliflozin ten. And furosemide forty in the morning.",
            ),
            (0, "Have you had any salty food recently, or been drinking more than usual?"),
            (1, "We had a family wedding last week. I ate a lot of machboos and probably drank too much."),
            (
                0,
                "Your blood pressure is one twelve over seventy, heart rate seventy-eight and regular. Oxygen ninety-five percent. I can hear some crackles at both lung bases, the neck veins are raised, and you have pitting oedema to mid-shin on both legs.",
            ),
            (
                0,
                "Your bloods from this morning show potassium four point eight and creatinine one hundred and twenty-four, which is about the same as last time. Your last echo showed an ejection fraction of thirty percent.",
            ),
            (
                0,
                "So you're more breathless with ordinary activity, which puts you in NYHA class three at the moment, and you've got fluid on board, most likely from the extra salt and fluid at the wedding.",
            ),
            (
                0,
                "I'm going to increase the furosemide to eighty milligrams in the morning for five days, then back to forty. Keep everything else the same for now. We won't increase the bisoprolol today because of the dizziness.",
            ),
            (
                0,
                "Keep your fluids to one and a half litres a day and go easy on the salt. Weigh yourself every morning, and if your weight goes up by more than two kilos in three days, call the heart failure nurse.",
            ),
            (
                0,
                "We'll repeat your kidney function and potassium in one week, and I'll see you back in clinic in two weeks.",
            ),
            (
                0,
                "If you become breathless at rest, have chest pain, or faint, come straight to the emergency department.",
            ),
            (1, "Understood, doctor. Thank you."),
        ],
    ),
    "af-review": (
        "AF clinic: anticoagulation review, 72-year-old woman",
        [
            (0, "Hello, Mrs. Fatima. This is your review for the atrial fibrillation. How have the palpitations been?"),
            (1, "Much better. Maybe one or two episodes a month, lasting about an hour. They go away on their own."),
            (0, "Any breathlessness, chest pain, or blackouts during the episodes?"),
            (1, "A little breathless, but no chest pain and I've never fainted."),
            (0, "You're on apixaban. What dose are you taking, and do you ever miss doses?"),
            (1, "Five milligrams, morning and evening. I use a pill box so I don't forget."),
            (0, "Any bleeding? Blood in the urine, black stools, nosebleeds, or easy bruising?"),
            (1, "My gums bleed a bit when I brush my teeth. Nothing else."),
            (0, "And what other tablets are you on?"),
            (
                1,
                "Bisoprolol two and a half milligrams, metformin, perindopril, and my GP started me on aspirin eighty-one milligrams a few months ago.",
            ),
            (0, "Do you have any allergies?"),
            (1, "No allergies."),
            (
                0,
                "Your weight today is fifty-eight kilos. Blood pressure one thirty-two over seventy-eight, and the heart rate is sixty-eight and regular. The ECG today shows sinus rhythm.",
            ),
            (0, "Your creatinine is ninety-eight, so your kidney function is fine."),
            (
                0,
                "With your age, high blood pressure, diabetes and being a woman, your CHA2DS2-VASc score is four, so you definitely need to stay on a blood thinner.",
            ),
            (
                0,
                "Only one of the dose-reduction criteria applies to you, the weight, so the full five milligram twice daily dose of apixaban is correct.",
            ),
            (
                0,
                "But you don't need the aspirin as well. Taking both raises the risk of bleeding and is probably why your gums bleed. Please stop the aspirin from today. I'll write to your GP.",
            ),
            (
                0,
                "Carry on with the bisoprolol. Since the episodes are short and infrequent, we'll keep a rate-control approach for now.",
            ),
            (
                0,
                "We'll check your kidney function and blood count again in six months, and I'll see you in clinic in six months.",
            ),
            (
                0,
                "If you have any black stools, vomit blood, or have a fall and hit your head, go to the emergency department straight away.",
            ),
            (1, "Okay. So no more aspirin. Thank you, doctor."),
        ],
    ),
    "post-pci": (
        "Post-PCI clinic: 6 weeks after NSTEMI and stent, 58-year-old man",
        [
            (0, "Mr. Yusuf, it's six weeks since your heart attack and the stent to the LAD. How are you feeling?"),
            (
                1,
                "Much better overall. No chest pain at all. I've been going to the cardiac rehab sessions twice a week.",
            ),
            (0, "That's excellent. Any breathlessness?"),
            (
                1,
                "Sometimes I feel I can't get a full breath, even when I'm sitting. It comes and goes. Not when I exercise particularly.",
            ),
            (0, "That can be a side effect of ticagrelor. Is it troubling you a lot?"),
            (1, "No, it's annoying but I can live with it."),
            (0, "Any bleeding or bruising?"),
            (1, "Some bruises on my arms, but nothing serious."),
            (0, "Which medicines are you taking now?"),
            (
                1,
                "Aspirin eighty-one, ticagrelor ninety twice a day, atorvastatin eighty, bisoprolol two point five, and ramipril five.",
            ),
            (0, "And the smoking?"),
            (1, "I stopped completely the day I was admitted. Not a single cigarette since."),
            (
                0,
                "Well done, that's the single most important thing. Your blood pressure is one twenty-four over seventy-six and heart rate sixty-two. Heart sounds are normal, chest is clear, and the radial access site on the right wrist has healed well.",
            ),
            (
                0,
                "Your echo before discharge showed an ejection fraction of fifty percent. Today your LDL cholesterol is one point eight millimoles per litre, which is still above our target of under one point four.",
            ),
            (0, "So I'd like to add ezetimibe ten milligrams once a day alongside the atorvastatin."),
            (
                0,
                "You need to stay on both aspirin and ticagrelor for twelve months from the stent, so until next September. Please don't stop the ticagrelor without speaking to us first, even if a dentist or another doctor asks you to, because that could block the stent.",
            ),
            (
                0,
                "The breathlessness is a known side effect and usually settles. If it gets worse, let us know and we can consider switching.",
            ),
            (0, "You can go back to work from next week, and carry on with the rehab programme."),
            (0, "We'll recheck the cholesterol and liver tests in eight weeks, and I'll see you in three months."),
            (1, "Thank you, doctor. I'll keep going."),
        ],
    ),
    "echo-dictation": (
        "Dictation: transthoracic echo report",
        [
            (
                0,
                "Transthoracic echocardiogram report for Mr. Ahmed, sixty-six years old. Indication: known heart failure with reduced ejection fraction, worsening breathlessness.",
            ),
            (0, "Image quality adequate. Sinus rhythm throughout the study."),
            (
                0,
                "The left ventricle is dilated, with an end-diastolic diameter of sixty-two millimetres. There is global hypokinesis, worse in the anterior wall and apex.",
            ),
            (
                0,
                "Left ventricular ejection fraction is thirty percent by Simpson's biplane. Grade two diastolic dysfunction, E over e prime of sixteen.",
            ),
            (0, "The right ventricle is normal in size with mildly reduced function. TAPSE sixteen millimetres."),
            (
                0,
                "The left atrium is severely dilated, indexed volume fifty-two millilitres per square metre. Right atrium normal.",
            ),
            (
                0,
                "Mitral valve: moderate functional mitral regurgitation. Aortic valve: trileaflet, no stenosis, trivial regurgitation. Tricuspid valve: mild regurgitation.",
            ),
            (
                0,
                "Estimated pulmonary artery systolic pressure forty-five millimetres of mercury. Inferior vena cava dilated at twenty-three millimetres with less than fifty percent inspiratory collapse.",
            ),
            (0, "No pericardial effusion. Aortic root normal size."),
            (
                0,
                "Conclusion: dilated left ventricle with severely impaired systolic function, ejection fraction thirty percent, unchanged from the previous study. Moderate functional mitral regurgitation. Raised filling pressures and estimated pulmonary pressure, consistent with fluid overload.",
            ),
        ],
    ),
}

_SECONDS_PER_WORD = 0.4


def list_samples() -> list[dict[str, str]]:
    return [{"id": k, "title": title} for k, (title, _) in _SCRIPTS.items()]


def get_sample(sample_id: str) -> Transcript | None:
    if sample_id not in _SCRIPTS:
        return None
    _, lines = _SCRIPTS[sample_id]
    segments, t = [], 0.0
    for i, (speaker, text) in enumerate(lines):
        dur = round(len(text.split()) * _SECONDS_PER_WORD, 1)
        segments.append(Segment(id=i, speaker=speaker, start=t, end=round(t + dur, 1), text=text))
        t = round(t + dur + 0.5, 1)
    return Transcript(segments=segments, provider="sample", duration=t)
