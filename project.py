from flask import Flask, render_template, request, jsonify
import json
from typing import Dict, List, Set, Tuple
import clips

app = Flask(__name__)

# ===========================
# CLIPS Expert System Integration
# ===========================

class CLIPSExpertSystem:
    def __init__(self):
        self.env = clips.Environment()
        self.setup_knowledge_base()
    
    def setup_knowledge_base(self):
        """Initialize CLIPS environment with rules and templates"""
        
        # 定义症状模板
        self.env.build("""
        (deftemplate symptom
            (slot name (type STRING))
            (slot value (type INTEGER)))
        """)
        
        # 定义指标模板
        self.env.build("""
        (deftemplate metric
            (slot name (type STRING))
            (slot value (type FLOAT)))
        """)
        
        # 定义专家系统结果模板
        self.env.build("""
        (deftemplate es_result
            (slot level (type STRING))
            (slot rule (type STRING))
            (slot explanation (type STRING)))
        """)
        
        # 定义推荐模板
        self.env.build("""
        (deftemplate recommendation
            (slot id (type STRING))
            (slot text (type STRING))
            (slot for_level (type STRING)))
        """)
        
        # 添加推荐事实
        recommendations = [
            ("rec_breaks", "Take 5-10 minute breaks every hour of study.", "high"),
            ("rec_counselor", "Consider discussing coping strategies with a counselor.", "high"),
            ("rec_sleep", "Maintain regular sleep schedule, avoid screens 60 minutes before bed.", "high"),
            ("rec_time_block", "Use time blocking for tasks with clear start and end times.", "high"),
            ("rec_plan", "Plan 3-5 priority tasks weekly, break them into subtasks.", "moderate"),
            ("rec_exercise", "Light exercise 3-4 times per week, 20-30 minutes each.", "moderate"),
            ("rec_peer", "Study with peers or communicate regularly to reduce isolation.", "moderate"),
            ("rec_monitor", "Maintain daily routine, record mood and sleep, review weekly.", "low")
        ]
        
        for rec_id, text, level in recommendations:
            self.env.assert_string(f'(recommendation (id "{rec_id}") (text "{text}") (for_level "{level}"))')
        
        # ==================== 症状评估规则 ====================
        
        # 规则1: 睡眠质量差 + 易怒 + 截止日期压力 → 高压症状
        self.env.build("""
        (defrule high-stress-symptom-1
            (symptom (name "poor_sleep") (value ?v1&:(>= ?v1 1)))
            (symptom (name "irritability") (value ?v2&:(>= ?v2 1)))
            (symptom (name "deadline_pressure") (value ?v3&:(>= ?v3 1)))
            =>
            (assert (symptom (name "stress_high_indicator") (value 1)))
            (assert (es_result 
                (level "high_risk") 
                (rule "high-stress-symptom-1")
                (explanation "Poor sleep, irritability, and deadline pressure detected")))
        )
        """)
        
        # 规则2: 持续疲劳 + 注意力不集中 → 高压症状
        self.env.build("""
        (defrule high-stress-symptom-2
            (symptom (name "persistent_fatigue") (value ?v1&:(>= ?v1 1)))
            (symptom (name "difficulty_concentrating") (value ?v2&:(>= ?v2 1)))
            =>
            (assert (symptom (name "stress_high_indicator") (value 1)))
            (assert (es_result 
                (level "high_risk") 
                (rule "high-stress-symptom-2")
                (explanation "Persistent fatigue and difficulty concentrating")))
        )
        """)
        
        # 规则3: 不吃饭 + 思绪纷乱 → 高压症状
        self.env.build("""
        (defrule high-stress-symptom-3
            (symptom (name "skip_meals") (value ?v1&:(>= ?v1 1)))
            (symptom (name "racing_thoughts") (value ?v2&:(>= ?v2 1)))
            =>
            (assert (symptom (name "stress_high_indicator") (value 1)))
            (assert (es_result 
                (level "high_risk") 
                (rule "high-stress-symptom-3")
                (explanation "Skipping meals and racing thoughts detected")))
        )
        """)
        
        # 规则4: 拖延 + 截止日期压力 → 中度压力
        self.env.build("""
        (defrule moderate-stress-symptom-1
            (symptom (name "procrastination") (value ?v1&:(>= ?v1 1)))
            (symptom (name "deadline_pressure") (value ?v2&:(>= ?v2 1)))
            (not (symptom (name "stress_high_indicator") (value ?v)))
            =>
            (assert (symptom (name "stress_moderate_indicator") (value 1)))
            (assert (es_result 
                (level "moderate_risk") 
                (rule "moderate-stress-symptom-1")
                (explanation "Procrastination with deadline pressure")))
        )
        """)
        
        # 规则5: 社交退缩 + 易怒 → 中度压力
        self.env.build("""
        (defrule moderate-stress-symptom-2
            (symptom (name "social_withdrawal") (value ?v1&:(>= ?v1 1)))
            (symptom (name "irritability") (value ?v2&:(>= ?v2 1)))
            (not (symptom (name "stress_high_indicator") (value ?v)))
            =>
            (assert (symptom (name "stress_moderate_indicator") (value 1)))
            (assert (es_result 
                (level "moderate_risk") 
                (rule "moderate-stress-symptom-2")
                (explanation "Social withdrawal and irritability")))
        )
        """)
        
        # 规则6: 轻度担忧 → 低压
        self.env.build("""
        (defrule low-stress-symptom
            (symptom (name "minor_worry_only") (value ?v1&:(>= ?v1 1)))
            (not (symptom (name "stress_high_indicator") (value ?v)))
            (not (symptom (name "stress_moderate_indicator") (value ?v)))
            =>
            (assert (symptom (name "stress_low_indicator") (value 1)))
            (assert (es_result 
                (level "low_risk") 
                (rule "low-stress-symptom")
                (explanation "Only minor worries detected")))
        )
        """)
        
        # ==================== 总体压力等级规则 ====================
        
        # 规则: 存在高压指标 → 总体高压
        self.env.build("""
        (defrule overall-high-stress
            (symptom (name "stress_high_indicator") (value ?v&:(>= ?v 1)))
            =>
            (assert (metric (name "overall") (value 4.0)))
            (assert (es_result 
                (level "very_high") 
                (rule "overall-high-stress")
                (explanation "Multiple high stress indicators present")))
        )
        """)
        
        # 规则: 存在中度压力指标 → 总体中度
        self.env.build("""
        (defrule overall-moderate-stress
            (symptom (name "stress_moderate_indicator") (value ?v&:(>= ?v 1)))
            (not (symptom (name "stress_high_indicator") (value ?v2)))
            =>
            (assert (metric (name "overall") (value 2.5)))
            (assert (es_result 
                (level "moderate") 
                (rule "overall-moderate-stress")
                (explanation "Moderate stress indicators present")))
        )
        """)
        
        # 规则: 存在低压指标 → 总体低压
        self.env.build("""
        (defrule overall-low-stress
            (symptom (name "stress_low_indicator") (value ?v&:(>= ?v 1)))
            (not (symptom (name "stress_high_indicator") (value ?v2)))
            (not (symptom (name "stress_moderate_indicator") (value ?v3)))
            =>
            (assert (metric (name "overall") (value 1.5)))
            (assert (es_result 
                (level "low") 
                (rule "overall-low-stress")
                (explanation "Only low stress indicators present")))
        )
        """)
        
        # ==================== 基于分数的后备规则 ====================
        
        # 创建全局变量来跟踪总体分数是否已设置
        self.env.build("""
        (deftemplate overall_set
            (slot is_set (type SYMBOL) (allowed-symbols TRUE FALSE))
        )
        """)
        
        # 修复后备规则：使用更好的方法检查事实是否存在
        # 方案1: 使用一个标记事实来跟踪
        self.env.build("""
        (defrule check-overall-not-set
            (not (metric (name "overall")))
            =>
            (assert (overall_set (is_set FALSE)))
        )
        """)
        
        self.env.build("""
        (defrule check-overall-set
            (metric (name "overall"))
            =>
            (assert (overall_set (is_set TRUE)))
        )
        """)
        
        # 修复后的后备规则：使用not模式
        self.env.build("""
        (defrule fallback-very-high-stress
            (metric (name "total_score") (value ?tv))
            (metric (name "max_score") (value ?mv))
            (not (metric (name "overall")))
            (test (> (/ ?tv ?mv) 0.8))
            =>
            (assert (metric (name "overall") (value 4.0)))
            (assert (es_result 
                (level "very_high") 
                (rule "fallback-score-very-high")
                (explanation "Based on total score > 80%")))
        )
        """)
        
        self.env.build("""
        (defrule fallback-high-stress
            (metric (name "total_score") (value ?tv))
            (metric (name "max_score") (value ?mv))
            (not (metric (name "overall")))
            (test (and (> (/ ?tv ?mv) 0.6) (<= (/ ?tv ?mv) 0.8)))
            =>
            (assert (metric (name "overall") (value 3.0)))
            (assert (es_result 
                (level "high") 
                (rule "fallback-score-high")
                (explanation "Based on total score 60-80%")))
        )
        """)
        
        self.env.build("""
        (defrule fallback-moderate-stress
            (metric (name "total_score") (value ?tv))
            (metric (name "max_score") (value ?mv))
            (not (metric (name "overall")))
            (test (and (> (/ ?tv ?mv) 0.4) (<= (/ ?tv ?mv) 0.6)))
            =>
            (assert (metric (name "overall") (value 2.0)))
            (assert (es_result 
                (level "moderate") 
                (rule "fallback-score-moderate")
                (explanation "Based on total score 40-60%")))
        )
        """)
        
        self.env.build("""
        (defrule fallback-low-stress
            (metric (name "total_score") (value ?tv))
            (metric (name "max_score") (value ?mv))
            (not (metric (name "overall")))
            (test (<= (/ ?tv ?mv) 0.4))
            =>
            (assert (metric (name "overall") (value 1.0)))
            (assert (es_result 
                (level "low") 
                (rule "fallback-score-low")
                (explanation "Based on total score <= 40%")))
        )
        """)
        
        # 方案2: 创建自定义函数（更高级的解决方案）
        # 首先定义自定义函数
        try:
            # 创建一个检查事实是否存在的函数
            self.env.build("""
            (deffunction overall-metric-exists ()
                (find-fact ((?f metric)) (eq ?f:name "overall"))
            )
            """)
        except:
            # 如果自定义函数创建失败，使用模式匹配方法
            print("Note: Using pattern matching instead of custom function")
        
        # ==================== 基于数值范围的规则 ====================
        
        self.env.build("""
        (defrule rule-very-high-overall
            (metric (name "overall") (value ?v))
            (test (>= ?v 4.0))
            =>
            (assert (es_result 
                (level "very_high") 
                (rule "rule-very-high-overall")
                (explanation "Overall stress score >= 4.0")))
        )
        """)
        
        self.env.build("""
        (defrule rule-high-overall
            (metric (name "overall") (value ?v))
            (test (and (>= ?v 3.0) (< ?v 4.0)))
            =>
            (assert (es_result 
                (level "high") 
                (rule "rule-high-overall")
                (explanation "Overall stress score 3.0-3.99")))
        )
        """)
        
        self.env.build("""
        (defrule rule-moderate-overall
            (metric (name "overall") (value ?v))
            (test (and (>= ?v 2.0) (< ?v 3.0)))
            =>
            (assert (es_result 
                (level "moderate") 
                (rule "rule-moderate-overall")
                (explanation "Overall stress score 2.0-2.99")))
        )
        """)
        
        self.env.build("""
        (defrule rule-low-overall
            (metric (name "overall") (value ?v))
            (test (< ?v 2.0))
            =>
            (assert (es_result 
                (level "low") 
                (rule "rule-low-overall")
                (explanation "Overall stress score < 2.0")))
        )
        """)
    
    def evaluate_responses(self, responses: Dict[str, int]) -> Dict[str, object]:
        """Evaluate stress using CLIPS expert system"""
        
        # 重置环境
        self.env.reset()
        
        # 转换响应为症状事实
        symptom_mapping = {
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
        
        # 添加症状事实
        for question, value in responses.items():
            if question in symptom_mapping and value in symptom_mapping[question]:
                symptom_name = symptom_mapping[question][value]
                self.env.assert_string(f'(symptom (name "{symptom_name}") (value 1))')
        
        # 添加总分事实
        total_score = sum(responses.values())
        max_score = len(responses) * 5
        self.env.assert_string(f'(metric (name "total_score") (value {total_score}))')
        self.env.assert_string(f'(metric (name "max_score") (value {max_score}))')
        
        # 运行推理
        self.env.run()
        
        # 收集结果
        results = {
            "stress_level": "Undetermined",
            "overall_score": 0.0,
            "rules_triggered": [],
            "explanations": [],
            "recommendations": [],
            "symptoms_detected": [],
            "initial_symptoms": []
        }
        
        # 获取所有事实
        for fact in self.env.facts():
            if fact.template.name == "es_result":
                level = str(fact["level"])
                rule = str(fact["rule"])
                explanation = str(fact["explanation"])
                
                results["rules_triggered"].append(rule)
                results["explanations"].append(explanation)
                
                # 确定最终压力等级（取最高等级）
                level_mapping = {
                    "very_high": 4,
                    "high": 3,
                    "moderate": 2,
                    "low": 1,
                    "high_risk": 4,
                    "moderate_risk": 3,
                    "low_risk": 2
                }
                
                current_level = results["stress_level"]
                current_priority = level_mapping.get(current_level, 0)
                new_priority = level_mapping.get(level, 0)
                
                if new_priority > current_priority:
                    results["stress_level"] = level.replace("_risk", "").title()
            
            elif fact.template.name == "metric" and str(fact["name"]) == "overall":
                results["overall_score"] = float(fact["value"])
            
            elif fact.template.name == "symptom":
                symptom_name = str(fact["name"])
                if "indicator" not in symptom_name:
                    results["symptoms_detected"].append(symptom_name)
                    # 也添加到初始症状列表
                    if symptom_name in ['poor_sleep', 'irritability', 'deadline_pressure', 'persistent_fatigue', 
                                       'difficulty_concentrating', 'skip_meals', 'racing_thoughts', 
                                       'procrastination', 'social_withdrawal', 'minor_worry_only']:
                        results["initial_symptoms"].append(symptom_name)
        
        # 获取推荐
        stress_level_lower = results["stress_level"].lower()
        for fact in self.env.facts():
            if fact.template.name == "recommendation":
                rec_level = str(fact["for_level"])
                if rec_level in stress_level_lower or stress_level_lower in rec_level:
                    results["recommendations"].append(str(fact["text"]))
        
        # 如果未确定等级，使用后备逻辑
        if results["stress_level"] == "Undetermined":
            score_ratio = total_score / max_score if max_score > 0 else 0
            if score_ratio > 0.8:
                results["stress_level"] = "Very High"
            elif score_ratio > 0.6:
                results["stress_level"] = "High"
            elif score_ratio > 0.4:
                results["stress_level"] = "Moderate"
            else:
                results["stress_level"] = "Low"
        
        return results

# 创建CLIPS专家系统实例
clips_expert = CLIPSExpertSystem()

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
# Rule Engine (保持原有规则引擎用于其他评估)
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

# ===========================
# Questions and Answer Scale
# ===========================

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

# ===========================
# Flask Routes
# ===========================

@app.route('/')
def index():
    return render_template('indexyu.html', questions=QUESTIONS, answer_scale=ANSWER_SCALE)

@app.route('/assess', methods=['POST'])
def assess():
    try:
        data = request.json
        name = data.get('name', '')
        responses = data.get('responses', {})
        
        # Convert string values to integers
        for key in responses:
            responses[key] = int(responses[key])
        
        # Create student and run rule-based assessment
        student = Student(name, responses)
        results = engine.run(student)
        
        # Run CLIPS expert system evaluation
        expert_results = clips_expert.evaluate_responses(responses)
        
        # Determine final stress level (优先使用CLIPS结果)
        clips_level = expert_results["stress_level"]
        if clips_level != "Undetermined":
            final_stress = clips_level
        else:
            final_stress = student.final_stress
        
        # 将CLIPS结果转换为用户友好的格式
        level_display = {
            "Very_High": "Very High",
            "High": "High",
            "Moderate": "Moderate",
            "Low": "Low",
            "Very High": "Very High",
            "High": "High",
            "Moderate": "Moderate",
            "Low": "Low"
        }
        final_stress_display = level_display.get(final_stress.replace(" ", "_"), final_stress)
        
        # Prepare response
        response_data = {
            'name': student.name,
            'final_stress': final_stress_display,
            'clips_stress_level': expert_results["stress_level"],
            'clips_overall_score': expert_results["overall_score"],
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
    print("Starting Student Stress Detection System with CLIPS Expert System...")
    print("Access the application at: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)