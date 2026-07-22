from __future__ import annotations


SUPPORTED_LANGUAGES = {"en", "zh-CN"}
DEFAULT_LANGUAGE = "en"


PROMPT_INTENTS = {
    "hearing_check": "confirm the participant can hear the caller clearly",
    "time_check": "confirm the participant is available to continue now",
    "permission_check": "obtain permission to continue follow-up questions",
    "identity_prompt": "collect participant name, mobile number, and age",
    "natural_intro": "introduce the check-in and collect participant name, mobile number, and age",
    "respondent_source": "classify whether the participant answers independently, with caregiver help, or by caregiver proxy",
    "average_pain_prompt": "collect average joint pain score over the past 24 hours on a 0 to 10 scale",
    "current_pain_prompt": "collect current joint pain score on a 0 to 10 scale",
    "pain_location": "collect the main pain location today",
    "functional_impact": "collect how pain affects daily function today",
    "comparison": "collect whether pain is better, worse, or the same as usual",
    "treatment": "collect current pain treatments or confirm none",
    "side_effects": "screen for side effects or new symptoms, including urgent symptoms",
    "side_effect_description": "collect a brief symptom description",
    "side_effect_start": "collect when the symptom started",
    "side_effect_status": "collect whether the symptom is ongoing or resolved",
    "side_effect_severity": "collect symptom severity as mild, moderate, severe, or unsure",
    "medication_changed": "collect whether medication was reduced, paused, or stopped because of symptoms",
    "doctor_contacted": "collect whether a doctor or clinic was contacted",
    "emergency_visit": "collect whether emergency care or hospitalization occurred",
    "red_flags": "screen for urgent red-flag symptoms requiring escalation",
    "survey_id": "collect the questionnaire participant ID",
    "oa_diagnosis": "confirm physician-diagnosed osteoarthritis status",
    "affected_joints": "collect affected joints using the questionnaire categories",
    "symptom_duration": "collect duration of joint pain, stiffness, or swelling",
    "last_flare_onset": "collect timing of the most recent pain flare",
    "last_flare_duration": "collect duration of the most recent pain flare",
    "last_flare_pain_score": "collect 0-10 pain score for the most recent flare",
    "annual_flare_frequency": "collect past-year flare frequency bucket",
    "usual_pain_response": "collect usual care-seeking or self-treatment behavior",
    "oral_painkiller_used": "confirm oral analgesic use during flares",
    "oral_painkiller_name": "collect oral analgesic name",
    "oral_painkiller_no_reason": "collect reason for no oral analgesic use",
    "adherence_to_doctor_order": "collect adherence to doctor's oral analgesic instructions",
    "missed_doses": "ask whether oral analgesic doses are sometimes forgotten",
    "stopped_after_improvement": "ask whether medication is stopped after symptom improvement",
    "difficulty_taking_as_directed": "ask whether scheduled dosing feels difficult",
    "missed_dose_reasons": "collect reasons for missed oral analgesic doses",
    "adverse_reactions": "screen adverse reactions during oral analgesic use",
    "adverse_reaction_symptoms": "collect adverse reaction symptom categories",
    "pain_improvement_after_meds": "collect pain improvement after medication",
    "function_improvement_after_meds": "collect daily activity improvement after medication",
    "consolidation_medication_willingness": "collect willingness for 1-2 week consolidation medication",
    "non_oral_treatments": "collect non-oral OA treatments",
    "painkiller_channels": "collect pain-medicine acquisition channels",
    "doctor_counseling": "collect hospital/community doctor medication counseling",
    "retail_pharmacy_reasons": "collect retail pharmacy purchase reasons",
    "retail_pharmacy_purchase_method": "collect retail pharmacy purchase method",
    "pharmacy_guidance_contraindications": "collect pharmacy contraindication guidance frequency",
    "pharmacy_guidance_dosage": "collect pharmacy dosage guidance frequency",
    "pharmacy_guidance_avoid_multiple_painkillers": "collect pharmacy multiple-painkiller warning frequency",
    "pharmacy_guidance_long_term_risks": "collect pharmacy long-term-risk guidance frequency",
}


STRINGS = {
    "en": {
        "intro": (
            "Hello, I'm calling from the research team for a short joint pain check-in. "
            "This is a research prototype, not an emergency or treatment service. "
            "Before we start, I just need to make sure the call is clear."
        ),
        "natural_intro": (
            "Hello, I'm calling from the research team for an osteoarthritis medication and treatment questionnaire. "
            "This is a research prototype, not an emergency or treatment service. I will ask one question at a time."
        ),
        "hearing_check": "Can you hear me clearly?",
        "time_check": "Is now a good time to continue?",
        "permission_check": "Would it be okay if I ask a few follow-up questions now?",
        "not_suitable_time": "No problem. We can stop here for now.",
        "permission_declined": "No problem. I will stop the check-in now.",
        "identity_prompt": "Could I confirm your name, mobile number, and age?",
        "respondent_source": (
            "Just to record this correctly, are you answering by yourself, "
            "answering with help from a caregiver, or is a caregiver answering for you?"
        ),
        "average_pain_prompt": (
            "Over the past day, what number best describes your average joint pain, from 0 to 10?"
        ),
        "current_pain_prompt": "And right now, what number would you give the pain, from 0 to 10?",
        "not_caught": "I didn't catch that. Could you please say that again?",
        "already_complete": "This check-in is complete. You can start a new one if needed.",
        "continue": "Let's continue with your pain check-in.",
        "missing_identity": "Thank you. Could I also have your {missing}?",
        "thanks_name_pain": "Thank you, {name}. {pain_prompt}",
        "invalid_pain_score": "For this question, I need a number from 0 to 10.",
        "pain_location": "Where are you feeling the pain today?",
        "functional_impact": (
            "How is the pain affecting your day? For example, walking, stairs, sleep, or using your hands."
        ),
        "comparison": "Compared with your usual pain, is this better, worse, or about the same?",
        "treatment": (
            "Are you using anything for the pain at the moment, such as tablets, cream, injections, or therapy?"
        ),
        "side_effects": (
            "Have you had any side effects or new symptoms, such as stomach trouble, swelling, rash, "
            "dizziness, or breathing problems?"
        ),
        "side_effect_description": "Could you briefly describe what you noticed?",
        "side_effect_start": "About when did it start?",
        "side_effect_status": "Is it still happening now, or has it resolved?",
        "side_effect_severity": "Would you say it was mild, moderate, severe, or are you not sure?",
        "medication_changed": "Because of this, did you reduce, pause, or stop any medicine?",
        "doctor_contacted": "Did you contact a doctor or clinic about it?",
        "emergency_visit": "Did you need emergency care or a hospital stay?",
        "red_flags": (
            "Last safety check. Have you had chest pain, trouble breathing, black stools, vomiting blood, "
            "fainting, confusion, or fever with a hot swollen joint?"
        ),
        "complete": "Thank you. That's all for now. I'll prepare the doctor report.",
        "got_it_treatment": "Got it. Are you using anything for the pain at the moment?",
        "ok_treatment": "Okay. Are you using anything for the pain at the moment?",
        "thanks_function": "Thanks. How is the pain affecting your day?",
        "ok_function": "Okay. How is the pain affecting your day?",
        "clarify_score": "Sorry, for this question please give a pain number from 0 to 10.",
        "escalation": (
            "I'm concerned about that. I can't diagnose it by phone, but it may need urgent care. "
            "Please call emergency services or seek urgent medical help now. "
            "If you are alone, please call someone nearby to stay with you."
        ),
        "identity_name": "name",
        "identity_mobile": "mobile number",
        "identity_age": "age",
        "none_reported": "none reported",
        "no_urgent_escalation": "no urgent escalation",
        "urgent_action": "urgent medical care / emergency services / contact caregiver",
        "prototype_disclaimer": "Research prototype -- not approved for clinical use or unsupervised participant contact.",
        "questionnaire_complete": "Thank you. The questionnaire is complete. I will prepare the structured report.",
    },
    "zh-CN": {
        "intro": (
            "您好，这里是北京大学研究团队，想做一个简短的关节疼痛随访。"
            "这是研究原型，不是急救或治疗服务。"
            "开始前，我先确认一下通话是否清楚。"
        ),
        "natural_intro": "您好，这里是北京大学研究团队，想做一个骨关节炎用药和治疗情况问卷。这是研究原型，不是急救或治疗服务。我会像电话访谈一样，一个问题一个问题问。",
        "hearing_check": "您能听清楚我说话吗？",
        "time_check": "现在方便继续吗？",
        "permission_check": "如果您现在方便，我可以继续问几个随访问题吗？",
        "not_suitable_time": "好的，那这次先到这里。",
        "permission_declined": "好的，我会停止这次随访。",
        "identity_prompt": "我先确认一下，您的姓名、手机号和年龄是多少？",
        "respondent_source": "为了记录准确，我想确认一下：现在是您本人自己回答，家属在旁边帮忙，还是由家属代您回答？",
        "average_pain_prompt": "回想过去一天，您的关节疼痛平均大概是0到10分里的几分？",
        "current_pain_prompt": "那现在这一刻，您会给这个疼痛打几分？0到10分。",
        "not_caught": "不好意思，我没听清。请您再说一遍。",
        "already_complete": "这次随访已经完成了。如有需要，可以重新开始。",
        "continue": "我们继续做疼痛随访。",
        "missing_identity": "谢谢。还需要确认一下您的{missing}。",
        "thanks_name_pain": "谢谢，{name}。{pain_prompt}",
        "invalid_pain_score": "这个问题需要记录一个0到10的数字。",
        "pain_location": "今天主要是哪个部位疼？",
        "functional_impact": "这个疼痛今天对您有什么影响？比如走路、上下楼、睡觉，或者用手。",
        "comparison": "和您平时相比，这次是轻一些、重一些，还是差不多？",
        "treatment": "您现在有没有用什么止痛办法？比如药片、药膏、针剂，或者康复治疗。",
        "side_effects": "最近有没有不舒服或新的症状？比如胃不舒服、肿胀、皮疹、头晕，或者喘不上气。",
        "side_effect_description": "能简单说一下您注意到的症状吗？",
        "side_effect_start": "大概什么时候开始的？",
        "side_effect_status": "现在还在持续吗，还是已经好了？",
        "side_effect_severity": "您觉得程度是轻度、中度、重度，还是不太确定？",
        "medication_changed": "因为这个情况，您有没有减少、暂停或停止用药？",
        "doctor_contacted": "有没有联系医生或门诊？",
        "emergency_visit": "有没有因此去急诊，或者住院？",
        "red_flags": "最后确认几个安全问题。有没有胸痛、喘不上气、黑便、吐血、晕倒、意识混乱，或者关节又红又热还发烧？",
        "complete": "谢谢。今天先问到这里。我会整理结构化报告。",
        "got_it_treatment": "明白了。您现在有没有用什么止痛办法？",
        "ok_treatment": "好的。您现在有没有用什么止痛办法？",
        "thanks_function": "谢谢。这个疼痛今天对您有什么影响？",
        "ok_function": "好的。这个疼痛今天对您有什么影响？",
        "clarify_score": "不好意思，这个问题请您说一个0到10的疼痛数字。",
        "escalation": (
            "这个情况我比较担心。电话里不能诊断，但可能需要尽快就医。"
            "请现在联系急救或尽快去急诊。"
            "如果您一个人在家，请马上联系家人或身边的人陪您。"
        ),
        "identity_name": "姓名",
        "identity_mobile": "手机号",
        "identity_age": "年龄",
        "none_reported": "未报告",
        "no_urgent_escalation": "未提示紧急升级",
        "urgent_action": "建议紧急就医 / 联系急救 / 联系家属或照护者",
        "prototype_disclaimer": "研究原型：尚未批准用于临床或无人监督的受试者联系。",
        "questionnaire_complete": "感谢您的参与，问卷已经完成。我会整理结构化报告。",
    },
}


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return str(language)
    return DEFAULT_LANGUAGE


def t(language: str | None, key: str, **kwargs: object) -> str:
    lang = normalize_language(language)
    template = STRINGS.get(lang, STRINGS[DEFAULT_LANGUAGE]).get(key, STRINGS[DEFAULT_LANGUAGE][key])
    if kwargs:
        return template.format(**kwargs)
    return template


def intent(key: str) -> str:
    return PROMPT_INTENTS.get(key, "")
