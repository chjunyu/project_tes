from flask import Flask, render_template, request, jsonify
import json
from typing import Dict, List, Set, Tuple

app = Flask(__name__)

# ===========================
# Expert System Rules
# ===========================

Rule = Tuple[List[str], str]

# Rule base: Explicit IF-THEN rules for forward chaining
RULES: List[Rule] = [
    (["poor_sleep", "irritability", "deadline_pressure"], "stress_high"),
    (["persistent_fatigue", "difficulty_concentrating"], "stress_high"),
    (["skip_meals", "racing_thoughts"], "stress_high"),
    (["procrastination", "deadline_pressure"], "stress_moderate"),
    (["social_withdrawal", "irritability"], "stress_moderate"),
    (["minor_worry_only"], "stress_low"),
    # Derive recommendations from stress level
    (["stress_high"], "rec_breaks"),
    (["stress_high"], "rec_counselor"),
    (["stress_high"], "rec_sleep"),
    (["stress_high"], "rec_time_block"),
    (["stress_moderate"], "rec_plan"),
    (["stress_moderate"], "rec_exercise"),
    (["stress_moderate"], "rec_peer"),
    (["stress_low"], "rec_monitor"),
]

# Explanation/Recommendation texts
EXPLANATIONS: Dict[str, str] = {
    "stress_high": "Multiple strong stress indicators, risk of burnout.",
    "stress_moderate": "Clear stress signals, manageable with structured approach.",
    "stress_low": "Mild stress, maintain observation.",
    "rec_breaks": "Take 5-10 minute breaks every hour of study.",
    "rec_counselor": "Consider discussing coping strategies with a counselor.",
    "rec_sleep": "Maintain regular sleep schedule, avoid screens 60 minutes before bed.",
    "rec_time_block": "Use time blocking for tasks with clear start and end times.",
    "rec_plan": "Plan 3-5 priority tasks weekly, break them into subtasks.",
    "rec_exercise": "Light exercise 3-4 times per week, 20-30 minutes each.",
    "rec_peer": "Study with peers or communicate regularly to reduce isolation.",
    "rec_monitor": "Maintain daily routine, record mood and sleep, review weekly.",
}

# Symptom mapping from questionnaire responses to expert system facts
SYMPTOM_MAPPING = {
    'sleep_quality': {
        4: 'poor_sleep',
        5: 'poor_sleep'
    },
    'irritability': {
        4: 'irritability',
        5: 'irritability'
    },
    'study_load': {
        4: 'deadline_pressure',
        5: 'deadline_pressure'
    },
    'depression': {
        4: 'persistent_fatigue',
        5: 'persistent_fatigue'
    },
    'academic_performance': {
        4: 'difficulty_concentrating',
        5: 'difficulty_concentrating'
    },
    'basic_needs': {
        4: 'skip_meals',
        5: 'skip_meals'
    },
    'anxiety_level': {
        4: 'racing_thoughts',
        5: 'racing_thoughts'
    },
    'future_career_concerns': {
        4: 'procrastination',
        5: 'procrastination'
    },
    'social_support': {
        1: 'social_withdrawal',
        2: 'social_withdrawal'
    },
    'peer_pressure': {
        1: 'minor_worry_only',
        2: 'minor_worry_only'
    }
}

def forward_chain(initial_facts: List[str]) -> Set[str]:
    """Forward chaining: Add conclusions when rule conditions are met until no new facts"""
    facts: Set[str] = set(initial_facts)
    changed = True
    while changed:
        changed = False
        for conditions, conclusion in RULES:
            if conclusion in facts:
                continue
            if all(cond in facts for cond in conditions):
                facts.add(conclusion)
                changed = True
    return facts

def classify_stress(facts: Set[str]) -> str:
    """Determine stress level by priority"""
    if "stress_high" in facts:
        return "High"
    if "stress_moderate" in facts:
        return "Moderate"
    if "stress_low" in facts:
        return "Low"
    return "Undetermined"

def evaluate_stress(responses: Dict[str, int]) -> Dict[str, object]:
    """Evaluate stress based on questionnaire responses"""
    # Convert responses to expert system facts
    initial_facts = []
    
    for question, value in responses.items():
        if question in SYMPTOM_MAPPING and value in SYMPTOM_MAPPING[question]:
            initial_facts.append(SYMPTOM_MAPPING[question][value])
    
    # Run forward chaining
    inferred_facts = forward_chain(initial_facts)
    
    # Classify stress level
    stress_level = classify_stress(inferred_facts)
    
    # Get recommendations
    recommendations = [EXPLANATIONS.get(fact, fact) for fact in inferred_facts if fact.startswith("rec_")]
    
    return {
        "stress_level": stress_level,
        "inferred_facts": sorted(inferred_facts),
        "recommendations": recommendations,
        "initial_facts": initial_facts
    }

# ===========================
# Student Class
# ===========================

class Student:
    def __init__(self, name, responses):
        self.name = name
        self.responses = responses
        
        # Map fields
        self.anxiety_level = responses.get('anxiety_level', 1)
        self.self_esteem = responses.get('self_esteem', 1)
        self.mental_health_history = responses.get('mental_health_history', 1)
        self.depression = responses.get('depression', 1)
        self.headache = responses.get('headache', 1)
        self.blood_pressure = responses.get('blood_pressure', 1)
        self.sleep_quality = responses.get('sleep_quality', 1)
        self.breathing_problem = responses.get('breathing_problem', 1)
        self.noise_level = responses.get('noise_level', 1)
        self.living_conditions = responses.get('living_conditions', 1)
        self.safety = responses.get('safety', 1)
        self.basic_needs = responses.get('basic_needs', 1)
        self.academic_performance = responses.get('academic_performance', 1)
        self.study_load = responses.get('study_load', 1)
        self.teacher_student_relationship = responses.get('teacher_student_relationship', 1)
        self.future_career_concerns = responses.get('future_career_concerns', 1)
        self.social_support = responses.get('social_support', 1)
        self.peer_pressure = responses.get('peer_pressure', 1)
        self.extracurricular_activities = responses.get('extracurricular_activities', 1)
        self.bullying = responses.get('bullying', 1)

        # Final outputs
        self.final_stress = "Low"
        self.reasons = []
        self.section_reasons = {
            "Mental State": [],
            "Physical Symptoms": [],
            "Environmental Factors": [],
            "Academic Pressure": [],
            "Social Support": []
        }


# ===========================
# Rule Engine
# ===========================

class RuleEngine:
    def __init__(self):
        self.rules = []
        self.triggered_rules = []

    def add_rule(self, condition, action, priority, name):
        self.rules.append((condition, action, priority, name))

    def run(self, student):
        results = []
        self.triggered_rules = []
        for condition, action, priority, name in sorted(self.rules, key=lambda x: x[2], reverse=True):
            if condition(student):
                output = action(student)
                if output:
                    results.append(output)
                self.triggered_rules.append(name)
        return results

    def explain(self):
        return self.triggered_rules


# ---------------------------
# QUESTIONS
# ---------------------------

QUESTIONS = {
    'anxiety_level': "How often do you feel anxious or tense?",
    'self_esteem': "How confident do you feel about yourself?",
    'mental_health_history': "Do you have a history of mental health issues?",
    'depression': "How often do you feel depressed or hopeless?",
    'headache': "How often do you experience headaches?",
    'blood_pressure': "How is your blood pressure level recently?",
    'sleep_quality': "How would you rate your sleep quality?",
    'breathing_problem': "Do you experience breathing difficulties?",
    'noise_level': "How noisy is your living or study environment?",
    'living_conditions': "How comfortable are your living conditions?",
    'safety': "How safe do you feel in your environment?",
    'basic_needs': "Are your basic needs (food, rest, hygiene) well supported?",
    'academic_performance': "How satisfied are you with your academic performance?",
    'study_load': "How heavy is your study load?",
    'teacher_student_relationship': "How is your relationship with teachers?",
    'future_career_concerns': "How worried are you about your future career?",
    'social_support': "How much social support do you receive?",
    'peer_pressure': "How strong is the peer pressure you feel?",
    'extracurricular_activities': "How often do you join extracurricular activities?",
    'bullying': "Have you experienced bullying?"
}


ANSWER_SCALE = {
    1: "Never / Very Good",
    2: "Rarely / Good",
    3: "Sometimes / Average",
    4: "Often / Poor",
    5: "Always / Very Poor"
}

# Initialize rule engine
engine = RuleEngine()

# ---- Critical Mental State ----
def critical_mental_health_rule(s):
    return (s.anxiety_level >= 4 and s.depression >= 4) or s.mental_health_history >= 4

def critical_mental_health_action(s):
    s.section_reasons["Mental State"].append("High anxiety and depression.")
    return f"🔴 Critical Mental Health Risk detected for {s.name}."

engine.add_rule(critical_mental_health_rule, critical_mental_health_action, 100, "Critical Mental State")

# ---- Physical Symptoms ----
def severe_physical_rule(s):
    return s.headache >= 4 and s.sleep_quality >= 4 and s.breathing_problem >= 4

def severe_physical_action(s):
    s.section_reasons["Physical Symptoms"].append("Severe physical symptoms (headache + sleep + breathing).")
    return f"🔴 Severe physical stress signals detected for {s.name}."

engine.add_rule(severe_physical_rule, severe_physical_action, 90, "Severe Physical Symptoms")

# ---- Bullying Crisis ----
def bullying_rule(s):
    return s.bullying >= 4

def bullying_action(s):
    s.section_reasons["Social Support"].append("Bullying experience detected.")
    return f"🔴 Bullying concern identified for {s.name}."

engine.add_rule(bullying_rule, bullying_action, 85, "Bullying Crisis")

# ---- Academic Pressure ----
def academic_pressure_rule(s):
    return s.study_load >= 4 and s.future_career_concerns >= 4

def academic_pressure_action(s):
    s.section_reasons["Academic Pressure"].append("Heavy study load and career concerns.")
    return f"🟡 Academic stress detected for {s.name}."

engine.add_rule(academic_pressure_rule, academic_pressure_action, 70, "Academic Pressure")

# ---- Environmental Stress ----
def environment_rule(s):
    return s.noise_level >= 4 or s.basic_needs >= 4 or s.living_conditions >= 4

def environment_action(s):
    s.section_reasons["Environmental Factors"].append("Poor environment or unmet basic needs.")
    return f"🟡 Environmental stress detected for {s.name}."

engine.add_rule(environment_rule, environment_action, 60, "Environmental Stress")

# ---- Social Isolation ----
def social_rule(s):
    return s.social_support <= 2 and s.peer_pressure >= 4

def social_action(s):
    s.section_reasons["Social Support"].append("Low support + high peer pressure.")
    return f"🟡 Social support issues detected for {s.name}."

engine.add_rule(social_rule, social_action, 55, "Social Support Issue")

# ---- Overall Score ----
def score_rule(s):
    return True

def score_action(s):
    total = sum(s.responses.values())
    max_score = len(s.responses) * 5
    stress = "Low"
    if total > 80: 
        stress = "Very High"
    elif total > 60: 
        stress = "High"
    elif total > 40: 
        stress = "Moderate"

    s.final_stress = stress
    return f"📊 Overall Stress Level for {s.name}: {stress}"

engine.add_rule(score_rule, score_action, 10, "Overall Score")

# ---------------------------
# Flask Routes
# ---------------------------

@app.route('/')
def index():
    return render_template('index.html', questions=QUESTIONS, answer_scale=ANSWER_SCALE)

@app.route('/assess', methods=['POST'])
def assess():
    try:
        data = request.json
        name = data.get('name', '')
        responses = data.get('responses', {})
        
        # Convert string values to integers
        for key in responses:
            responses[key] = int(responses[key])
        
        # Create student and run assessment
        student = Student(name, responses)
        results = engine.run(student)
        
        # Run expert system evaluation
        expert_results = evaluate_stress(responses)
        
        # Combine results - prefer expert system stress level if available
        final_stress = expert_results["stress_level"] if expert_results["stress_level"] != "Undetermined" else student.final_stress
        
        # Prepare response
        response_data = {
            'name': student.name,
            'final_stress': final_stress,
            'results': results,
            'section_reasons': student.section_reasons,
            'triggered_rules': engine.explain(),
            'total_score': sum(student.responses.values()),
            'max_score': len(student.responses) * 5,
            'expert_system': expert_results
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Student Stress Detection System...")
    print("Access the application at: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)