; -----------------------------
; Fever Expert System (Forward Chaining)
; -----------------------------

(deftemplate patient
  (slot temperature (type FLOAT))
  (slot days (type INTEGER)) ; typhoid severity rule uses 10-14 days
)

(deftemplate symptom
  (slot name (type SYMBOL))
)

(deftemplate fever
  (slot level (type SYMBOL)) ; none lowfever high veryhigh
)

(deftemplate vote
  (slot disease (type SYMBOL)) ; malaria dengue typhoid
  (slot points (type INTEGER))
  (slot reason (type STRING))
)

(deftemplate diagnosis
  (slot disease (type SYMBOL))
  (slot confidence (type INTEGER))
)

(deftemplate malaria_vote
  (slot subtype (type SYMBOL)) ; PF PV PO PM
  (slot points (type INTEGER))
  (slot reason (type STRING))
)

(deftemplate malaria_subtype
  (slot subtype (type SYMBOL))
  (slot confidence (type INTEGER))
)

(deftemplate severity
  (slot disease (type SYMBOL))
  (slot level (type SYMBOL)) ; low/high/veryhigh
  (slot reason (type STRING))
)

; -----------------------------
; Fever severity rules (1-4)
; -----------------------------

(defrule fever_none
  (patient (temperature ?t&:(= ?t 37.0)))
  =>
  (assert (fever (level none)))
)

(defrule fever_low
  (patient (temperature ?t&:(and (> ?t 37.0) (<= ?t 38.30))))
  =>
  (assert (fever (level lowfever)))
)

(defrule fever_high
  (patient (temperature ?t&:(and (> ?t 38.30) (<= ?t 39.40))))
  =>
  (assert (fever (level high)))
)

(defrule fever_veryhigh
  (patient (temperature ?t&:(> ?t 39.40)))
  =>
  (assert (fever (level veryhigh)))
)

; -----------------------------
; Disease votes (rules 6-32 mapped as scoring)
; You can adjust points if needed.
; -----------------------------

(defrule body_aches_vote
  (symptom (name bodyachesorpains))
  =>
  (assert (vote (disease malaria) (points 2) (reason "Body aches/pains")))
  (assert (vote (disease dengue)  (points 2) (reason "Body aches/pains")))
)

(defrule chills_vote
  (symptom (name chills))
  =>
  (assert (vote (disease malaria) (points 2) (reason "Chills")))
  (assert (vote (disease dengue)  (points 2) (reason "Chills")))
)

(defrule fever_high_vote
  (fever (level high))
  =>
  (assert (vote (disease malaria) (points 2) (reason "High fever range")))
  (assert (vote (disease typhoid) (points 2) (reason "High fever range")))
  (assert (vote (disease dengue)  (points 2) (reason "High fever range")))
)

(defrule headache_vote
  (symptom (name headache))
  =>
  (assert (vote (disease malaria) (points 1) (reason "Headache")))
  (assert (vote (disease typhoid) (points 1) (reason "Headache")))
  (assert (vote (disease dengue)  (points 1) (reason "Headache")))
)

(defrule nausea_vomiting_vote
  (symptom (name nauseaorvomiting))
  =>
  (assert (vote (disease malaria) (points 1) (reason "Nausea/Vomiting")))
  (assert (vote (disease dengue)  (points 1) (reason "Nausea/Vomiting")))
)

(defrule excessive_sweating_vote
  (symptom (name excessivesweating))
  =>
  (assert (vote (disease malaria) (points 1) (reason "Excessive sweating")))
)

(defrule dark_urine_vote
  (symptom (name darkcoloredurine))
  =>
  (assert (vote (disease malaria) (points 2) (reason "Dark colored urine")))
)

(defrule weakness_vote
  (symptom (name weakness_generalized))
  =>
  (assert (vote (disease malaria) (points 1) (reason "Generalized weakness")))
)

(defrule jointaches_vote
  (symptom (name jointaches))
  =>
  (assert (vote (disease dengue)  (points 2) (reason "Joint aches")))
  (assert (vote (disease typhoid) (points 1) (reason "Joint aches")))
)

(defrule diarrhea_vote
  (symptom (name diarrhea))
  =>
  (assert (vote (disease dengue)  (points 1) (reason "Diarrhea")))
  (assert (vote (disease typhoid) (points 2) (reason "Diarrhea")))
)

(defrule fatigue_vote
  (symptom (name fatigue))
  =>
  (assert (vote (disease dengue)  (points 1) (reason "Fatigue")))
  (assert (vote (disease typhoid) (points 1) (reason "Fatigue")))
)

(defrule skinrash_vote
  (symptom (name skinrash))
  =>
  (assert (vote (disease dengue)  (points 2) (reason "Skin rash")))
  (assert (vote (disease typhoid) (points 1) (reason "Skin rash")))
)

(defrule pain_discomfort_vote
  (symptom (name painordiscomfort))
  =>
  (assert (vote (disease typhoid) (points 1) (reason "Pain/discomfort")))
)

(defrule confusion_vote
  (symptom (name confusion))
  =>
  (assert (vote (disease typhoid) (points 2) (reason "Confusion")))
)

(defrule decreased_appetite_vote
  (symptom (name decreased_appetite))
  =>
  (assert (vote (disease typhoid) (points 1) (reason "Decreased appetite")))
)

(defrule disorientation_vote
  (symptom (name disorientation))
  =>
  (assert (vote (disease typhoid) (points 2) (reason "Disorientation")))
)

; -----------------------------
; Malaria subtype votes (33-56 mapped)
; Only used if malaria wins.
; -----------------------------

(defrule malaria_dizziness_pf
  (symptom (name dizziness))
  =>
  (assert (malaria_vote (subtype PF) (points 2) (reason "Dizziness -> P.F.")))
)

(defrule malaria_fatigue_subtypes
  (symptom (name fatigue))
  =>
  (assert (malaria_vote (subtype PF) (points 1) (reason "Fatigue -> P.F.")))
  (assert (malaria_vote (subtype PV) (points 1) (reason "Fatigue -> P.V.")))
  (assert (malaria_vote (subtype PO) (points 1) (reason "Fatigue -> P.O.")))
)

(defrule malaria_fever_all
  (fever (level ?lvl&:(neq ?lvl none)))
  =>
  (assert (malaria_vote (subtype PF) (points 1) (reason "Fever -> P.F.")))
  (assert (malaria_vote (subtype PV) (points 1) (reason "Fever -> P.V.")))
  (assert (malaria_vote (subtype PO) (points 1) (reason "Fever -> P.O.")))
  (assert (malaria_vote (subtype PM) (points 1) (reason "Fever -> P.M.")))
)

(defrule malaria_chills_subtypes
  (symptom (name chills))
  =>
  (assert (malaria_vote (subtype PV) (points 1) (reason "Chills -> P.V.")))
  (assert (malaria_vote (subtype PO) (points 1) (reason "Chills -> P.O.")))
  (assert (malaria_vote (subtype PM) (points 1) (reason "Chills -> P.M.")))
)

(defrule malaria_diarrhea_subtypes
  (symptom (name diarrhea))
  =>
  (assert (malaria_vote (subtype PV) (points 1) (reason "Diarrhea -> P.V.")))
  (assert (malaria_vote (subtype PO) (points 1) (reason "Diarrhea -> P.O.")))
)

(defrule malaria_pf_severe_cluster
  (or (symptom (name abdominalpain))
      (symptom (name musclepain))
      (symptom (name enlargement_spleen))
      (symptom (name backpain))
      (symptom (name jointaches))
      (symptom (name seizures))
      (symptom (name vomiting))
      (symptom (name severeanemia))
      (symptom (name headache)))
  =>
  (assert (malaria_vote (subtype PF) (points 2) (reason "Severe cluster -> P.F.")))
)

(defrule malaria_pm_highgrade
  (symptom (name highgradefever))
  =>
  (assert (malaria_vote (subtype PM) (points 2) (reason "High grade fever -> P.M.")))
)

(defrule malaria_po_africa
  (symptom (name travel_africa))
  =>
  (assert (malaria_vote (subtype PO) (points 3) (reason "Travel history Africa -> P.O.")))
)

; -----------------------------
; Dengue severity rules (57-66) as forward chaining
; Note: Your rule list has duplicates (Highfever -> high AND veryhigh).
; We'll use symptoms to push severity.
; -----------------------------

(defrule dengue_sev_highfever_high
  (symptom (name highfever))
  =>
  (assert (severity (disease dengue) (level high) (reason "High fever"))))

(defrule dengue_sev_highfever_veryhigh
  (symptom (name highfever))
  =>
  (assert (severity (disease dengue) (level veryhigh) (reason "High fever (risk)"))))

(defrule dengue_sev_anorexia
  (symptom (name anorexia))
  =>
  (assert (severity (disease dengue) (level high) (reason "Anorexia"))))

(defrule dengue_sev_vomit_pain
  (symptom (name vomiting_abdominalpain))
  =>
  (assert (severity (disease dengue) (level high) (reason "Vomiting + abnormal pain"))))

(defrule dengue_sev_hemorrhagic
  (symptom (name haemorrhagicdiathesis))
  =>
  (assert (severity (disease dengue) (level high) (reason "Haemorrhagic diathesis"))))

(defrule dengue_sev_hematuria
  (symptom (name hematuria))
  =>
  (assert (severity (disease dengue) (level high) (reason "Hematuria"))))

(defrule dengue_sev_liver
  (symptom (name enlargement_liver))
  =>
  (assert (severity (disease dengue) (level high) (reason "Enlarged liver"))))

(defrule dengue_sev_bleeding
  (symptom (name bleeding_major))
  =>
  (assert (severity (disease dengue) (level veryhigh) (reason "Bleeding (nose/gums/hematemesis)"))))

(defrule dengue_sev_refusal
  (symptom (name refusal_food_drink))
  =>
  (assert (severity (disease dengue) (level veryhigh) (reason "Refusal to food/drink"))))

(defrule dengue_sev_breath
  (symptom (name difficulty_breathing))
  =>
  (assert (severity (disease dengue) (level veryhigh) (reason "Difficulty breathing"))))

; -----------------------------
; Typhoid severity rule (67)
; -----------------------------

(defrule typhoid_sev_days
  (patient (days ?d&:(and (>= ?d 10) (<= ?d 14))))
  =>
  (assert (severity (disease typhoid) (level high) (reason "10-14 days suffering"))))
