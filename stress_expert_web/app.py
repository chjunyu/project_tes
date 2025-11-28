from flask import Flask, render_template, request
from clips import Environment

app = Flask(__name__)

# ------------------------------
# 1. 创建 CLIPS 环境 + 模板 + 规则
# ------------------------------

env = Environment()

# 用一个 metric 模板来保存整体压力评分
env.build(r"""
(deftemplate metric
    (slot name)
    (slot value (type FLOAT)))
""")

# 用 es_result 保存推理结果（等级 + 使用的规则）
env.build(r"""
(deftemplate es_result
    (slot level)
    (slot rule))
""")

# 规则：根据 overall 压力分数决定等级
# >=4.0 : very_high
env.build(r"""
(defrule very-high-stress
    (metric (name overall) (value ?v))
    (test (>= ?v 4.0))
 =>
    (assert (es_result
        (level very_high)
        (rule "rule-very-high-overall")))
)
""")

# 3.0–3.99 : high
env.build(r"""
(defrule high-stress
    (metric (name overall) (value ?v))
    (test (and (>= ?v 3.0) (< ?v 4.0)))
 =>
    (assert (es_result
        (level high)
        (rule "rule-high-overall")))
)
""")

# 2.0–2.99 : moderate
env.build(r"""
(defrule moderate-stress
    (metric (name overall) (value ?v))
    (test (and (>= ?v 2.0) (< ?v 3.0)))
 =>
    (assert (es_result
        (level moderate)
        (rule "rule-moderate-overall")))
)
""")

# <2.0 : low
env.build(r"""
(defrule low-stress
    (metric (name overall) (value ?v))
    (test (< ?v 2.0))
 =>
    (assert (es_result
        (level low)
        (rule "rule-low-overall")))
)
""")


# ------------------------------
# 2. Python 这边负责把 1–5 题目变成 overall_score
# ------------------------------

NEGATIVE_KEYS = ["anxiety_level", "depression", "study_load"]   # 分数越高 = 压力越大
POSITIVE_KEYS = ["self_esteem", "sleep_quality"]                # 分数越高 = 状态越好 → 压力越小


def to_stress_score(key: str, value: int) -> int:
    """把 1–5 转成压力分数 1–5，正向题用 6-value 反转。"""
    if key in POSITIVE_KEYS:
        return 6 - value  # 5->1  (很好变低压), 1->5 (很差变高压)
    return value


def run_inference_with_clips(responses: dict):
    """
    responses 例子：
    {
      "anxiety_level": 4,
      "self_esteem": 2,
      "depression": 5,
      "sleep_quality": 3,
      "study_load": 4
    }
    这里：
    1) Python 算压力分数 + overall 平均
    2) 把 overall 丢给 CLIPSpy，让 CLIPS 规则分类
    """

    # 1. 各题压力分数
    stress_scores = {}
    for k, v in responses.items():
        stress_scores[k] = to_stress_score(k, v)

    all_scores = list(stress_scores.values())
    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # 2. 把 overall 丢给 CLIPS 环境
    env.reset()
    env.assert_string(f"(metric (name overall) (value {overall}))")
    env.run()

    # 3. 从 es_result 里面取出 level & rule
    level_symbol = "unknown"
    triggered_rule = "none"

    for fact in env.facts():
        if fact.template.name == "es_result":
            level_symbol = str(fact["level"])
            triggered_rule = str(fact["rule"])
            break

    # 4. 映射成可读的 stress level 文本
    symbol_to_label = {
        "very_high": "Very High",
        "high": "High",
        "moderate": "Moderate",
        "low": "Low",
        "unknown": "Unknown",
    }
    stress_level = symbol_to_label.get(level_symbol, "Unknown")

    # 5. 给一个简单建议（你之后可以自己改）
    if stress_level == "Very High":
        advice = ("Your stress level is VERY HIGH. Please seek professional help "
                  "and talk to your counsellor or trusted people as soon as possible.")
    elif stress_level == "High":
        advice = ("Your stress level is HIGH. Try to reduce workload, improve sleep quality, "
                  "and practice relaxation techniques.")
    elif stress_level == "Moderate":
        advice = ("Your stress level is MODERATE. You may feel pressure but it is manageable. "
                  "Maintain healthy routines and monitor your feelings.")
    elif stress_level == "Low":
        advice = ("Your stress level is LOW. Keep your current habits and coping strategies.")
    else:
        advice = ("Unable to clearly determine your stress level. "
                  "Please review your situation or consult a professional if needed.")

    return stress_level, advice, overall, stress_scores, triggered_rule


# ------------------------------
# 3. 路由：index + diagnose
# ------------------------------

@app.route("/", methods=["GET"])
def index():
    # 显示你的 index.html（问卷页面）
    return render_template("index.html")


@app.route("/diagnose", methods=["POST"])
def diagnose():
    # 从表单拿 5 题，一定要和 index.html 的 name 一致
    try:
        anxiety = int(request.form.get("anxiety_level"))
        self_esteem = int(request.form.get("self_esteem"))
        depression = int(request.form.get("depression"))
        sleep_quality = int(request.form.get("sleep_quality"))
        study_load = int(request.form.get("study_load"))
    except Exception:
        return "Form data error: please answer all questions.", 400

    responses = {
        "anxiety_level": anxiety,
        "self_esteem": self_esteem,
        "depression": depression,
        "sleep_quality": sleep_quality,
        "study_load": study_load,
    }

    # 调用 CLIPSpy + 规则推理
    stress_level, advice, overall, stress_scores, triggered_rule = run_inference_with_clips(responses)

    # 把结果传给 result.html
    return render_template(
        "result.html",
        stress_level=stress_level,
        advice=advice,
        overall=round(overall, 2),
        scores=responses,          # 原始 1–5
        stress_scores=stress_scores,  # 转换后的压力分数
        triggered_rule=triggered_rule
    )


if __name__ == "__main__":
    # 记得先 cd 到 stress_expert_web 再跑：python app.py
    app.run(debug=True)
