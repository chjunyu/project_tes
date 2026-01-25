import clips

# -----------------------------
# Setup CLIPS environment
# -----------------------------
env = clips.Environment()
env.load("clips_rules.clp")

# -----------------------------
# Helper Functions
# -----------------------------
def fact_exists(template_name, slot_name=None, value=None):
    for fact in env.facts():
        if fact.template.name != template_name:
            continue
        if slot_name is None:
            return True
        if fact[slot_name] == value:
            return True
    return False

def count_facts(template_name, slot_name=None, value=None):
    count = 0
    for fact in env.facts():
        if fact.template.name != template_name:
            continue
        if slot_name is None or fact[slot_name] == value:
            count += 1
    return count

# -----------------------------
# Combined Patient Scenario Tests
# -----------------------------
def test_scenarios():
    print("=== Combined Patient Scenarios ===")

    scenarios = [
        {
            "name": "Malaria PF Severe Cluster",
            "patient": {"temperature": 39.5, "days": 0},
            "symptoms": ["chills", "dizziness", "abdominalpain", "headache", "fatigue"],
            "expected_votes": ["malaria"],
            "expected_subtypes": ["PF", "PV", "PO", "PM"],  # PF should be dominant due to cluster
            "expected_severity": []
        },
        {
            "name": "Dengue High Severity",
            "patient": {"temperature": 39.0, "days": 0},
            "symptoms": ["highfever", "vomiting_abdominalpain", "bleeding_major", "skinrash", "anorexia"],
            "expected_votes": ["dengue"],
            "expected_subtypes": [],
            "expected_severity": ["high", "veryhigh"]
        },
        {
            "name": "Typhoid Mid Severity",
            "patient": {"temperature": 38.5, "days": 12},
            "symptoms": ["headache", "jointaches", "diarrhea", "decreased_appetite"],
            "expected_votes": ["typhoid"],
            "expected_subtypes": [],
            "expected_severity": ["high"]
        },
        {
            "name": "Malaria + Typhoid Mixed",
            "patient": {"temperature": 39.0, "days": 11},
            "symptoms": ["chills", "fatigue", "darkcoloredurine", "diarrhea", "confusion"],
            "expected_votes": ["malaria", "typhoid"],
            "expected_subtypes": ["PF", "PV", "PO"],
            "expected_severity": ["high"]  # Typhoid 10-14 days triggers high
        }
    ]

    for scenario in scenarios:
        env.reset()
        # Assert patient facts
        patient = scenario["patient"]
        if patient["temperature"] > 0:
            env.assert_string(f"(patient (temperature {patient['temperature']}) (days {patient['days']}))")
        else:
            env.assert_string(f"(patient (days {patient['days']}))")

        # Assert symptoms
        for symptom in scenario["symptoms"]:
            if symptom.startswith("fever_"):
                fever_level = symptom.split("_")[1]
                env.assert_string(f"(fever (level {fever_level}))")
            else:
                env.assert_string(f"(symptom (name {symptom}))")

        env.run()

        # Check disease votes
        votes_pass = all(fact_exists("vote", "disease", d) for d in scenario["expected_votes"])
        # Check malaria subtypes
        subtypes_pass = all(fact_exists("malaria_vote", "subtype", s) for s in scenario["expected_subtypes"])
        # Check severity
        severity_pass = all(fact_exists("severity", "level", s) for s in scenario["expected_severity"])

        print(f"Scenario: {scenario['name']}")
        print(f"  Disease Votes Expected: {scenario['expected_votes']} -> {'PASS' if votes_pass else 'FAIL'}")
        if scenario["expected_subtypes"]:
            print(f"  Malaria Subtypes Expected: {scenario['expected_subtypes']} -> {'PASS' if subtypes_pass else 'FAIL'}")
        if scenario["expected_severity"]:
            print(f"  Severity Levels Expected: {scenario['expected_severity']} -> {'PASS' if severity_pass else 'FAIL'}")
        print("")

# -----------------------------
# Run All Tests (Single + Scenarios)
# -----------------------------
def run_all_tests():
    # Optional: run individual rule tests first
    # from previous test functions: test_fever_severity(), test_votes(), etc.
    test_scenarios()
    print("=== ALL SCENARIOS TESTED ===")

if __name__ == "__main__":
    run_all_tests()
