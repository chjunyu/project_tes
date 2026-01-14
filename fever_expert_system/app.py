import os
from flask import Flask, request, jsonify, send_from_directory, redirect
from clips import Environment, Router

# -------------------------
# Paths
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

RULE_FILE = os.path.join(BASE_DIR, "clips_rules.clp")


# -------------------------
# CLIPS Error Router (capture warnings/errors)
# -------------------------
class CLIPSErrorRouter(Router):
    def __init__(self):
        super().__init__("pyerr", 10)
        self.messages = []

    def query(self, name):
        return name in ("werror", "error", "warning")

    def write(self, name, message):
        self.messages.append(message)

    def read(self, name):
        return ""

    def unread(self, name, count):
        return 0

    def exit(self, exitcode):
        return


# -------------------------
# Symptom mapping (checkbox key -> label)
# key 必须和 CLIPS 的 (symptom (name <key>)) 一致
# -------------------------
SYMPTOMS = [
    ("bodyachesorpains", "Body aches or pains"),
    ("chills", "Chills"),
    ("headache", "Headache"),
    ("nauseaorvomiting", "Nausea or vomiting"),
    ("excessivesweating", "Excessive sweating"),
    ("darkcoloredurine", "Dark colored urine"),
    ("weakness_generalized", "Weakness (generalized)"),
    ("jointaches", "Joint aches"),
    ("diarrhea", "Diarrhea"),
    ("fatigue", "Fatigue"),
    ("skinrash", "Skin rash"),
    ("painordiscomfort", "Pain or discomfort"),
    ("confusion", "Confusion"),
    ("decreased_appetite", "Decreased appetite"),
    ("disorientation", "Disorientation"),

    # dengue severity related
    ("highfever", "High fever (Dengue severity)"),
    ("anorexia", "Anorexia"),
    ("vomiting_abdominalpain", "Vomiting and abnormal pain"),
    ("haemorrhagicdiathesis", "Haemorrhagic diathesis"),
    ("hematuria", "Hematuria"),
    ("enlargement_liver", "Enlargement of the liver"),
    ("bleeding_major", "Bleeding nose/gums, hematemesis"),
    ("refusal_food_drink", "Refusal to food or drink"),
    ("difficulty_breathing", "Difficulty in breathing"),

    # malaria subtype extras
    ("dizziness", "Dizziness"),
    ("abdominalpain", "Abdominal pain"),
    ("musclepain", "Muscle pain"),
    ("enlargement_spleen", "Enlargement of the spleen"),
    ("backpain", "Back pain"),
    ("seizures", "Seizures"),
    ("vomiting", "Vomiting (Malaria subtype)"),
    ("severeanemia", "Severe anemia"),
    ("highgradefever", "High grade fever (P.M.)"),
    ("travel_africa", "Recent travel history to Africa"),
]


def run_inference(temperature: float, days: int, selected_syms: list[str]):
    """
    Forward chaining in CLIPS.
    We assert:
      - (patient (temperature X) (days Y))
      - (symptom (name <key>))

    Rules assert:
      - (fever (level ...))
      - (vote (disease ...) (points ...) (reason ...))
      - (severity (disease ...) (level ...) (reason ...))
      - (malaria_vote (subtype ...) (points ...) (reason ...))
    """
    env = Environment()

    err_router = CLIPSErrorRouter()
    env.add_router(err_router)

    # Debug prints (useful for rule file path issues)
    print("=== DEBUG ===")
    print("CWD:", os.getcwd())
    print("BASE_DIR:", BASE_DIR)
    print("RULE_FILE:", RULE_FILE)
    print("RULE exists:", os.path.exists(RULE_FILE))
    print("=============")

    try:
        env.load(RULE_FILE)
    except Exception as e:
        details = "".join(err_router.messages) or "No CLIPS error output captured."
        raise RuntimeError(
            "CLIPS failed to load rule file.\n"
            f"RULE_FILE: {RULE_FILE}\n"
            "---- CLIPS DETAILS ----\n"
            + details
        ) from e

    env.reset()

    env.assert_string(f"(patient (temperature {temperature}) (days {days}))")
    for s in selected_syms:
        env.assert_string(f"(symptom (name {s}))")

    env.run()

    # -------------------------
    # Extract fever level
    # -------------------------
    fever_level = None
    for fact in env.facts():
        if fact.template.name == "fever":
            fever_level = str(fact["level"])
            break

    # -------------------------
    # Sum votes for diseases
    # -------------------------
    disease_scores = {"malaria": 0, "dengue": 0, "typhoid": 0}
    disease_reasons = {"malaria": [], "dengue": [], "typhoid": []}

    for fact in env.facts():
        if fact.template.name == "vote":
            d = str(fact["disease"])
            p = int(fact["points"])
            r = str(fact["reason"])
            if d in disease_scores:
                disease_scores[d] += p
                disease_reasons[d].append(f"+{p}: {r}")

    # deterministic tie-break: score desc, then malaria>dengue>typhoid (optional)
    ranked = sorted(
        disease_scores.items(),
        key=lambda x: (x[1], x[0] == "malaria", x[0] == "dengue"),
        reverse=True,
    )
    best_disease, best_score = ranked[0]

    # -------------------------
    # Malaria subtype (only meaningful if malaria wins)
    # -------------------------
    malaria_subtype = None
    malaria_subtype_score = 0
    malaria_reasons = []

    if best_disease == "malaria":
        subtype_scores = {"PF": 0, "PV": 0, "PO": 0, "PM": 0}
        subtype_reasons = {"PF": [], "PV": [], "PO": [], "PM": []}

        for fact in env.facts():
            if fact.template.name == "malaria_vote":
                st = str(fact["subtype"])
                p = int(fact["points"])
                r = str(fact["reason"])
                if st in subtype_scores:
                    subtype_scores[st] += p
                    subtype_reasons[st].append(f"+{p}: {r}")

        st_ranked = sorted(
            subtype_scores.items(),
            key=lambda x: (x[1], x[0] == "PF"),
            reverse=True,
        )
        malaria_subtype, malaria_subtype_score = st_ranked[0]
        malaria_reasons = subtype_reasons[malaria_subtype]

    # -------------------------
    # Severity (FIXED):
    # only take severity facts that match best_disease,
    # and select the worst level (veryhigh > high > low)
    # -------------------------
    severity_map = {"low": 1, "high": 2, "veryhigh": 3}
    best_sev_val = 0
    severity_level = None
    severity_reasons = []

    for fact in env.facts():
        if fact.template.name != "severity":
            continue

        d = str(fact["disease"])
        if d != best_disease:
            continue

        lvl = str(fact["level"])
        val = severity_map.get(lvl, 0)
        reason = str(fact["reason"])

        if val > best_sev_val:
            best_sev_val = val
            severity_level = lvl
            severity_reasons = [reason]
        elif val == best_sev_val and val != 0:
            severity_reasons.append(reason)

    return {
        "fever_level": fever_level,
        "disease_scores": disease_scores,
        "disease_reasons": disease_reasons,
        "best_disease": best_disease,
        "best_score": best_score,
        "malaria_subtype": malaria_subtype,
        "malaria_subtype_score": malaria_subtype_score,
        "malaria_reasons": malaria_reasons,
        "severity_level": severity_level,
        "severity_reasons": severity_reasons,
        "selected_symptoms": selected_syms,
    }


# -------------------------
# Pages: serve plain HTML (no template engine)
# -------------------------
@app.get("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.get("/result")
def result_page():
    return send_from_directory(app.template_folder, "result.html")


@app.get("/diagnose")
def diagnose_redirect():
    # prevents manual /diagnose browsing from showing 404
    return redirect("/")


# -------------------------
# API: symptoms for index.html
# -------------------------
@app.get("/api/symptoms")
def api_symptoms():
    return jsonify({"symptoms": [{"key": k, "label": v} for (k, v) in SYMPTOMS]})


# -------------------------
# API: diagnose (JSON in, JSON out)
# -------------------------
@app.post("/api/diagnose")
def api_diagnose():
    data = request.get_json(silent=True) or {}

    try:
        temperature = float(data.get("temperature", 37.0))
    except (TypeError, ValueError):
        temperature = 37.0

    try:
        days = int(data.get("days", 0))
    except (TypeError, ValueError):
        days = 0

    selected = data.get("symptoms", []) or []
    if not isinstance(selected, list):
        selected = []

    valid_keys = {k for (k, _) in SYMPTOMS}
    selected = [s for s in selected if s in valid_keys]

    result = run_inference(temperature, days, selected)

    return jsonify(
        {
            "input": {"temperature": temperature, "days": days, "symptoms": selected},
            "result": result,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
