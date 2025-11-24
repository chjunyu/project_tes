import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Set, Tuple

# 规则类型：条件列表 -> 结论
Rule = Tuple[List[str], str]

# 规则库：显式 IF-THEN 规则，用于前向链推理
RULES: List[Rule] = [
    (["poor_sleep", "irritability", "deadline_pressure"], "stress_high"),
    (["persistent_fatigue", "difficulty_concentrating"], "stress_high"),
    (["skip_meals", "racing_thoughts"], "stress_high"),
    (["procrastination", "deadline_pressure"], "stress_moderate"),
    (["social_withdrawal", "irritability"], "stress_moderate"),
    (["minor_worry_only"], "stress_low"),
    # 从压力等级继续推导管理建议
    (["stress_high"], "rec_breaks"),
    (["stress_high"], "rec_counselor"),
    (["stress_high"], "rec_sleep"),
    (["stress_high"], "rec_time_block"),
    (["stress_moderate"], "rec_plan"),
    (["stress_moderate"], "rec_exercise"),
    (["stress_moderate"], "rec_peer"),
    (["stress_low"], "rec_monitor"),
]

# 解释/建议文本
EXPLANATIONS: Dict[str, str] = {
    "stress_high": "多项强烈压力指标，存在倦怠风险。",
    "stress_moderate": "有明显压力信号，可通过结构化管理缓解。",
    "stress_low": "轻度压力，保持观察。",
    "rec_breaks": "每学习 1 小时插入 5–10 分钟休息。",
    "rec_counselor": "考虑与辅导员/咨询师沟通应对策略。",
    "rec_sleep": "固定睡眠作息，睡前 60 分钟避免屏幕。",
    "rec_time_block": "用时间分块安排任务，设定清晰起止。",
    "rec_plan": "每周规划 3–5 个优先事项，拆解为子任务。",
    "rec_exercise": "每周 3–4 次、每次 20–30 分钟轻运动。",
    "rec_peer": "与同伴结伴学习或定期交流，减少孤立感。",
    "rec_monitor": "保持日常作息，记录情绪与睡眠，按周复盘。",
}

# 症状选项及展示名称
SYMPTOMS: Dict[str, str] = {
    "poor_sleep": "Poor sleep (≥3 nights/week)",
    "irritability": "Irritability",
    "deadline_pressure": "Deadlines within 7 days",
    "persistent_fatigue": "Persistent fatigue",
    "difficulty_concentrating": "Difficulty concentrating",
    "skip_meals": "Skipping meals",
    "racing_thoughts": "Racing thoughts about school",
    "procrastination": "Frequent procrastination",
    "social_withdrawal": "Social withdrawal",
    "minor_worry_only": "Minor worry only",
}


def forward_chain(initial_facts: List[str]) -> Set[str]:
    """前向链推理：满足规则条件则添加结论，直到无新事实"""
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
    """按优先级选定压力等级"""
    if "stress_high" in facts:
        return "high"
    if "stress_moderate" in facts:
        return "moderate"
    if "stress_low" in facts:
        return "low"
    return "undetermined"


def evaluate(symptoms: List[str]) -> Dict[str, object]:
    """外部调用接口：输入症状列表，返回推理结果"""
    inferred = forward_chain(symptoms)
    level = classify_stress(inferred)
    recs = [fact for fact in inferred if fact.startswith("rec_")]
    return {
        "stress_level": level,
        "inferred_facts": sorted(inferred),
        "recommendations": [EXPLANATIONS.get(rec, rec) for rec in recs],
    }


class StressApp(tk.Tk):
    """简单 GUI：勾选症状，点击 Evaluate 显示结果，可重复评估"""

    def __init__(self):
        super().__init__()
        self.title("Academic Stress Expert System")
        self.resizable(False, False)
        self.vars: Dict[str, tk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """构建界面控件"""
        tk.Label(self, text="Select symptoms to evaluate:").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        frame = tk.Frame(self)
        frame.grid(row=1, column=0, sticky="w", padx=12)

        for idx, (key, label) in enumerate(SYMPTOMS.items()):
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame, text=label, variable=var, anchor="w", justify="left")
            chk.grid(row=idx, column=0, sticky="w")
            self.vars[key] = var

        buttons = tk.Frame(self)
        buttons.grid(row=2, column=0, sticky="w", padx=12, pady=(8, 4))
        ttk.Button(buttons, text="Evaluate", command=self.on_evaluate).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Reset", command=self.on_reset).grid(row=0, column=1)

        self.result_txt = tk.Text(self, width=60, height=16, state="disabled")
        self.result_txt.grid(row=3, column=0, padx=12, pady=(4, 12))

    def on_evaluate(self) -> None:
        """收集症状，调用推理引擎，并渲染结果"""
        selected_keys = [key for key, var in self.vars.items() if var.get()]
        result = evaluate(selected_keys)

        selected_labels = [SYMPTOMS.get(key, key) for key in selected_keys]
        inferred_labels = [SYMPTOMS.get(fact, EXPLANATIONS.get(fact, fact)) for fact in result["inferred_facts"]]
        recs = result["recommendations"]
        stress = result["stress_level"]
        explanation = EXPLANATIONS.get("stress_" + stress, "") if stress != "undetermined" else "未确定"

        lines: List[str] = []
        lines.append("已选择症状:")
        if selected_labels:
            lines.extend([f"  - {item}" for item in selected_labels])
        else:
            lines.append("  - 无")

        lines.append(f"\n压力等级: {stress}")
        lines.append(f"解释: {explanation}")

        lines.append("\n推理得到事实:")
        if inferred_labels:
            lines.extend([f"  - {item}" for item in inferred_labels])
        else:
            lines.append("  - 无")

        lines.append("\n建议:")
        if recs:
            lines.extend([f"  - {rec}" for rec in recs])
        else:
            lines.append("  - 暂无（证据不足）")

        self.result_txt.configure(state="normal")
        self.result_txt.delete("1.0", tk.END)
        self.result_txt.insert(tk.END, "\n".join(lines))
        self.result_txt.configure(state="disabled")

    def on_reset(self) -> None:
        """清空勾选与结果，便于重复评估"""
        for var in self.vars.values():
            var.set(False)
        self.result_txt.configure(state="normal")
        self.result_txt.delete("1.0", tk.END)
        self.result_txt.configure(state="disabled")


def main() -> None:
    """启动 GUI 应用"""
    app = StressApp()
    app.mainloop()


if __name__ == "__main__":
    main()
