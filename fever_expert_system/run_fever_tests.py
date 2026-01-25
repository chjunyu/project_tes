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
    """
    Check if a fact exists. Optionally check slot name and value.
    """
    for fact in env.facts():
        if fact.template.name != template_name:
            continue
        if slot_name is None:
            return True
        if fact[slot_name] == value:
            return True
    return False

def count_facts(template_name, slot_name=None, value=None):
    """
    Count the number of facts that match the template/slot/value.
    """
    count = 0
    for fact in env.facts():
        if fact.template.name != template_name:
            continue
        if slot_name is None or fact[slot_name] == value:
            count += 1
    return count

# -----------------------------
# Fever Severity Tests (Rules 1-4)
# -----------------------------
def test_fever_severity():
    print("=== Fever Severity Tests ===")
    tests = [
        (37.0, "none"),
        (38.0, "lowfever"),
        (39.0, "high"),
        (40.0, "veryhigh")
    ]
    for temp, expected in tests:
        env.reset()
        env.assert_string(f"(patient (temperature {temp}))")
        env.run()
        result = "PASS" if fact_exists("fever", "level", expected) else "FAIL"
        print(f"Temperature {temp} -> Fever {expected}: {result}")

# -----------------------------
# Disease Vote Tests (Rules 6-32)
# -----------------------------
def test_votes():
    print("\n=== Disease Vote Tests ===")
    symptom_votes = {
        "bodyachesorpains": ["malaria", "dengue"],
        "chills": ["malaria", "dengue"],
        "headache": ["malaria", "typhoid", "dengue"],
        "nauseaorvomiting": ["malaria", "dengue"],
        "excessivesweating": ["malaria"],
        "darkcoloredurine": ["malaria"],
        "weakness_generalized": ["malaria"],
        "jointaches": ["dengue", "typhoid"],
        "diarrhea": ["dengue", "typhoid"],
        "fatigue": ["dengue", "typhoid"],
        "skinrash": ["dengue", "typhoid"],
        "painordiscomfort": ["typhoid"],
        "confusion": ["typhoid"],
        "decreased_appetite": ["typhoid"],
        "disorientation": ["typhoid"]
    }

    for symptom, expected_diseases in symptom_votes.items():
        env.reset()
        env.assert_string(f"(symptom (name {symptom}))")
        env.run()
        passed = all(fact_exists("vote", "disease", d) for d in expected_diseases)
        print(f"Symptom {symptom} -> Votes {expected_diseases}: {'PASS' if passed else 'FAIL'}")

# -----------------------------
# Malaria Subtype Tests (Rules 33-56)
# -----------------------------
def test_malaria_subtypes():
    print("\n=== Malaria Subtype Tests ===")
    tests = [
        ("dizziness", ["PF"]),
        ("fatigue", ["PF", "PV", "PO"]),
        ("fever_high", ["PF", "PV", "PO", "PM"]),
        ("chills", ["PV", "PO", "PM"]),
        ("diarrhea", ["PV", "PO"]),
        ("abdominalpain", ["PF"]),
        ("musclepain", ["PF"]),
        ("enlargement_spleen", ["PF"]),
        ("backpain", ["PF"]),
        ("jointaches", ["PF"]),
        ("seizures", ["PF"]),
        ("vomiting", ["PF"]),
        ("severeanemia", ["PF"]),
        ("headache", ["PF"]),
        ("highgradefever", ["PM"]),
        ("travel_africa", ["PO"])
    ]

    for symptom, expected_subtypes in tests:
        env.reset()
        if symptom.startswith("fever_"):
            level = symptom.split("_")[1]
            env.assert_string(f"(fever (level {level}))")
        else:
            env.assert_string(f"(symptom (name {symptom}))")
        env.run()
        passed = all(fact_exists("malaria_vote", "subtype", s) for s in expected_subtypes)
        print(f"Symptom {symptom} -> Malaria Subtypes {expected_subtypes}: {'PASS' if passed else 'FAIL'}")

# -----------------------------
# Dengue Severity Tests (Rules 57-66)
# -----------------------------
def test_dengue_severity():
    print("\n=== Dengue Severity Tests ===")
    tests = {
        "highfever": ["high", "veryhigh"],
        "anorexia": ["high"],
        "vomiting_abdominalpain": ["high"],
        "haemorrhagicdiathesis": ["high"],
        "hematuria": ["high"],
        "enlargement_liver": ["high"],
        "bleeding_major": ["veryhigh"],
        "refusal_food_drink": ["veryhigh"],
        "difficulty_breathing": ["veryhigh"]
    }

    for symptom, levels in tests.items():
        env.reset()
        env.assert_string(f"(symptom (name {symptom}))")
        env.run()
        passed = all(fact_exists("severity", "level", lvl) for lvl in levels)
        print(f"Symptom {symptom} -> Severity Levels {levels}: {'PASS' if passed else 'FAIL'}")

# -----------------------------
# Typhoid Severity Tests (Rule 67)
# -----------------------------
def test_typhoid_severity():
    print("\n=== Typhoid Severity Tests ===")
    env.reset()
    env.assert_string("(patient (days 12))")
    env.run()
    result = "PASS" if fact_exists("severity", "disease", "typhoid") else "FAIL"
    print("Typhoid 10-14 days -> Severity High:", result)

# -----------------------------
# Run All Tests
# -----------------------------
def run_all_tests():
    test_fever_severity()
    test_votes()
    test_malaria_subtypes()
    test_dengue_severity()
    test_typhoid_severity()
    print("\n=== ALL RULES TESTED ===")

if __name__ == "__main__":
    run_all_tests()
