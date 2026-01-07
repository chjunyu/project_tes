import os
from flask import Flask, render_template, request
from clips import Environment, Router

# -------------------------
# Paths (IMPORTANT)
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Force Flask to use the correct folders under fever_expert_system/
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Use absolute path so CLIPS can always find the rules file
RULE_FILE = os.path.join(BASE_DIR, "clips_rules.clp")


# -------------------------
# CLIPS Error Router (to show real CLIPS load/parse errors)
# -------------------------
class CLIPSErrorRouter(Router):
    def __init__(self):
        super().__init__("pyerr", 10)
        self.messages = []

    def query(self, name):
        # capture warnings + errors from CLIPS
        return name in ("werror", "error", "warning")

    def write(self, name, message):
        self.messages.append(message)

    def read(self, name):
        return ""

    def unread(self, name, count):
        return 0

    def exit(self, exitcode):
        return


# ---- Symptom mapping: UI checkbox name -> CLIPS symbol ----
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
    Forward chaining using CLIPS (clipspy).
    Working memory is populated by (patient ...) and (symptom ...) facts.
    Rules assert (fever ...), (vote ...), (severity ...), (malaria_vote ...) facts.
    """
    env = Environment()

    # Capture CLIPS errors/warnings to show real details
    err_router = CLIPSErrorRouter()
    env.add_router(err_router)

    # Debug prints (see console)
    print("=== DEBUG ===")
    print("CWD:", os.getcwd())
    print("BASE_DIR:", BASE_DIR)
    print("RULE_FILE:", RULE_FILE)
    print("RULE exists:", os.path.exists(RULE_FILE))
    print("=============")

    # Load rule base
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

    # Assert patient data
    env.assert_string(f'(patient (temperature {temperature}) (days {days}))')

    # Assert symptoms
    for s in selected_syms:
        env.assert_string(f'(symptom (name {s}))')

    # Forward chaining
    env.run()

    # Extract fever level
    fever_level = None
    for fact in env.facts():
        if fact.template.name == "fever":
            fever_level = str(fact["level"])
            break

    # Sum votes for disease
    disease_scores = {"malaria": 0, "dengue": 0, "typhoid": 0}
    reasons = {"malaria": [], "dengue": [], "typhoid": []}

    for fact in env.facts():
        if fact.template.name == "vote":
            d = str(fact["disease"])
            p = int(fact["points"])
            r = str(fact["reason"])
            if d in disease_scores:
                disease_scores[d] += p
                reasons[d].append(f"+{p}: {r}")

    # Pick best disease (deterministic tie-break)
    ranked = sorted(
        disease_scores.items(),
        key=lambda x: (x[1], x[0] == "malaria", x[0] == "dengue"),
        reverse=True,
    )
    best_disease, best_score = ranked[0]

    # If malaria is best, compute subtype
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

    # Severity extraction (choose worst: veryhigh > high > low)
    severity_map = {"low": 1, "high": 2, "veryhigh": 3}
    found_sev = []
    for fact in env.facts():
        if fact.template.name == "severity":
            found_sev.append(
                {
                    "disease": str(fact["disease"]),
                    "level": str(fact["level"]),
                    "reason": str(fact["reason"]),
                }
            )

    best_sev_level = None
    best_sev_reasons = []
    best_val = 0
    for s in found_sev:
        if s["disease"] == best_disease:
            val = severity_map.get(s["level"], 0)
            if val > best_val:
                best_val = val
                best_sev_level = s["level"]
                best_sev_reasons = [s["reason"]]
            elif val == best_val and val != 0:
                best_sev_reasons.append(s["reason"])

    return {
        "fever_level": fever_level,
        "disease_scores": disease_scores,
        "disease_reasons": reasons,
        "best_disease": best_disease,
        "best_score": best_score,
        "malaria_subtype": malaria_subtype,
        "malaria_subtype_score": malaria_subtype_score,
        "malaria_reasons": malaria_reasons,
        "severity_level": best_sev_level,
        "severity_reasons": best_sev_reasons,
    }


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", symptoms=SYMPTOMS)


@app.route("/diagnose", methods=["POST"])
def diagnose():
    # Read inputs
    try:
        temperature = float(request.form.get("temperature", "37.0"))
    except ValueError:
        temperature = 37.0

    try:
        days = int(request.form.get("days", "0"))
    except ValueError:
        days = 0

    selected = request.form.getlist("symptoms")

    result = run_inference(temperature, days, selected)

    return render_template(
        "result.html",
        temperature=temperature,
        days=days,
        selected=selected,
        symptoms_dict=dict(SYMPTOMS),
        result=result,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
