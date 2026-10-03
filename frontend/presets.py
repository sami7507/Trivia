"""
Example patients for the "Quick start" menu (pure data — no Streamlit import, so it is unit-testable).

`level` is the triage level the example is designed to demonstrate:
    3 = Resuscitation 🟣 · 2 = Urgent 🔴 · 1 = Semi-Urgent 🟠 · 0 = Non-Urgent 🟢
Every example is checked against the schema and the model in tests/test_presets.py.
"""
import random
from typing import Dict, List

DOT = {3: "🟣", 2: "🔴", 1: "🟠", 0: "🟢"}
LEVEL_NAME = {3: "Resuscitation", 2: "Urgent", 1: "Semi-Urgent", 0: "Non-Urgent"}

NORMAL_ADULT = dict(age=40, heart_rate=78, systolic_bp=120, diastolic_bp=78, temperature=36.8,
                    respiratory_rate=16, oxygen_saturation=98, pain_scale=0,
                    chief_complaint="headache", arrival_mode="walk_in", consciousness="alert")


def _p(level, title, age, hr, sbp, dbp, temp, rr, spo2, pain, cc, arrival, cons):
    return dict(level=level, title=title, data=dict(
        age=age, heart_rate=hr, systolic_bp=sbp, diastolic_bp=dbp, temperature=temp,
        respiratory_rate=rr, oxygen_saturation=spo2, pain_scale=pain,
        chief_complaint=cc, arrival_mode=arrival, consciousness=cons))


PRESET_LIST: List[dict] = [
    # ── 🟣 Resuscitation ───────────────────────────────────────────────
    _p(3, "Chest pain with shock", 65, 130, 85, 55, 39.2, 28, 87, 9, "chest_pain", "ambulance", "verbal"),
    _p(3, "Collapsed and unresponsive", 58, 38, 70, 40, 36.0, 8, 78, 0, "syncope", "ambulance", "unresponsive"),
    _p(3, "Severe trauma — blood loss", 34, 142, 74, 42, 35.8, 32, 86, 9, "trauma", "helicopter", "pain_response"),
    _p(3, "Anaphylaxis (severe allergy)", 27, 150, 78, 40, 37.0, 34, 84, 3, "allergic_reaction", "ambulance", "verbal"),
    _p(3, "Septic shock — confused, high fever", 72, 128, 82, 46, 39.8, 30, 88, 4, "altered_mental_status", "ambulance", "verbal"),
    _p(3, "Respiratory failure", 68, 128, 100, 62, 37.6, 36, 80, 4, "shortness_of_breath", "ambulance", "verbal"),
    # ── 🔴 Urgent ──────────────────────────────────────────────────────
    _p(2, "Suspected heart attack", 58, 108, 152, 92, 37.0, 22, 93, 8, "chest_pain", "ambulance", "alert"),
    _p(2, "Possible stroke", 71, 100, 190, 105, 37.1, 20, 93, 4, "altered_mental_status", "ambulance", "verbal"),
    _p(2, "Severe asthma attack", 22, 124, 130, 82, 37.2, 28, 91, 3, "shortness_of_breath", "ambulance", "alert"),
    _p(2, "Pneumonia with high fever", 66, 114, 128, 74, 38.9, 26, 91, 5, "fever", "walk_in", "alert"),
    _p(2, "Major fracture after fall", 45, 116, 140, 86, 37.0, 24, 94, 9, "fracture", "ambulance", "alert"),
    _p(2, "Acute abdomen (possible appendicitis)", 29, 112, 128, 80, 38.6, 24, 94, 8, "abdominal_pain", "walk_in", "alert"),
    _p(2, "Fast irregular heartbeat", 63, 146, 112, 66, 37.0, 24, 94, 2, "palpitations", "ambulance", "alert"),
    # ── 🟠 Semi-Urgent ─────────────────────────────────────────────────
    _p(1, "Moderate abdominal pain", 42, 104, 118, 76, 38.1, 20, 95, 7, "abdominal_pain", "walk_in", "alert"),
    _p(1, "Severe migraine with vomiting", 35, 96, 134, 84, 37.3, 18, 98, 8, "headache", "walk_in", "alert"),
    _p(1, "Dizzy spells (older adult)", 74, 90, 146, 88, 37.1, 18, 96, 3, "dizziness", "walk_in", "alert"),
    _p(1, "Palpitations, feeling anxious", 41, 106, 132, 82, 37.1, 19, 97, 2, "palpitations", "walk_in", "alert"),
    _p(1, "Allergic reaction with wheezing", 30, 106, 122, 76, 37.4, 22, 94, 5, "allergic_reaction", "walk_in", "alert"),
    _p(1, "Severe back pain", 52, 94, 138, 86, 37.3, 18, 97, 8, "back_pain", "walk_in", "alert"),
    _p(1, "Vomiting and dehydration", 27, 104, 112, 70, 37.9, 19, 97, 4, "nausea_vomiting", "walk_in", "alert"),
    _p(1, "Fever for three days", 48, 100, 126, 80, 38.4, 19, 96, 4, "fever", "walk_in", "alert"),
    # ── 🟢 Non-Urgent ──────────────────────────────────────────────────
    _p(0, "Small cut on the hand", 24, 74, 122, 80, 36.7, 15, 99, 2, "laceration", "walk_in", "alert"),
    _p(0, "Mild headache", 31, 76, 120, 78, 36.8, 15, 99, 3, "headache", "walk_in", "alert"),
    _p(0, "Twisted ankle", 26, 78, 124, 80, 36.8, 15, 99, 4, "trauma", "walk_in", "alert"),
    _p(0, "Cold with low fever", 38, 84, 122, 78, 37.8, 16, 98, 2, "fever", "walk_in", "alert"),
    _p(0, "Mild lower-back ache", 44, 74, 126, 82, 36.7, 15, 99, 3, "back_pain", "walk_in", "alert"),
    _p(0, "Upset stomach", 23, 80, 118, 74, 36.9, 15, 99, 2, "nausea_vomiting", "walk_in", "alert"),
    _p(0, "Minor skin laceration, healthy senior", 68, 72, 130, 80, 36.6, 15, 98, 2, "laceration", "walk_in", "alert"),
]

CUSTOM_LABEL = "✏️ Custom entry — start from a normal adult"


def label(p: dict) -> str:
    return f"{DOT[p['level']]} {LEVEL_NAME[p['level']]} · {p['title']}"


PRESETS: Dict[str, dict] = {CUSTOM_LABEL: NORMAL_ADULT}
PRESETS.update({label(p): p["data"] for p in PRESET_LIST})


def random_patient(rng: random.Random = None) -> Dict[str, object]:
    """A random but plausible patient (any acuity) for the 🎲 button."""
    rng = rng or random.Random()
    sev = rng.choices([0, 1, 2, 3], weights=[35, 30, 25, 10])[0]
    mean = {  # (mean, sd) by severity
        "age": [(40, 18), (46, 18), (56, 18), (62, 16)], "heart_rate": [(78, 9), (94, 11), (112, 14), (136, 16)],
        "systolic_bp": [(122, 10), (128, 14), (140, 20), (84, 14)], "temperature": [(36.8, .3), (37.6, .5), (38.4, .7), (38.9, .8)],
        "respiratory_rate": [(16, 2), (19, 2), (24, 3), (30, 4)], "oxygen_saturation": [(98, 1), (96, 1.5), (93, 2), (86, 3)],
        "pain_scale": [(2, 1.5), (5, 2), (7, 1.5), (8, 1.5)]}

    def g(k, lo, hi, nd=0):
        m, s = mean[k][sev]
        v = min(hi, max(lo, rng.gauss(m, s)))
        return round(v, nd) if nd else int(round(v))

    sbp = g("systolic_bp", 60, 220)
    complaints = {0: ["laceration", "headache", "back_pain", "nausea_vomiting", "fever", "trauma"],
                  1: ["abdominal_pain", "headache", "dizziness", "fever", "palpitations", "back_pain"],
                  2: ["chest_pain", "shortness_of_breath", "fracture", "abdominal_pain", "fever", "syncope"],
                  3: ["chest_pain", "shortness_of_breath", "trauma", "altered_mental_status", "syncope"]}[sev]
    return dict(
        age=g("age", 1, 100), heart_rate=g("heart_rate", 40, 190), systolic_bp=sbp,
        diastolic_bp=max(25, min(sbp - 15, int(sbp * rng.uniform(0.55, 0.68)))),
        temperature=g("temperature", 35.5, 41.0, 1), respiratory_rate=g("respiratory_rate", 8, 45),
        oxygen_saturation=g("oxygen_saturation", 70, 100), pain_scale=g("pain_scale", 0, 10),
        chief_complaint=rng.choice(complaints),
        arrival_mode=rng.choices(["walk_in", "ambulance", "police", "helicopter"],
                                 weights=[[85, 12, 2, 1], [65, 30, 3, 2], [30, 62, 5, 3], [8, 70, 7, 15]][sev])[0],
        consciousness=rng.choices(["alert", "verbal", "pain_response", "unresponsive"],
                                  weights=[[97, 3, 0, 0], [92, 7, 1, 0], [70, 20, 8, 2], [10, 30, 30, 30]][sev])[0])
