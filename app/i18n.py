from __future__ import annotations


SUPPORTED_LANGUAGES = {"en", "zh-CN"}
DEFAULT_LANGUAGE = "en"


STRINGS = {
    "en": {
        "intro": (
            "Hello, I'm a researcher from Peking University Medical Hospital. "
            "This is a research prototype, not an emergency or treatment service. "
            "I'm calling for a short joint pain check-in."
        ),
        "hearing_check": "Can you hear me clearly?",
        "time_check": "Is now a good time to continue?",
        "permission_check": "May I continue with the follow-up questions?",
        "not_suitable_time": "No problem. We can stop here for now.",
        "permission_declined": "No problem. I will stop the check-in now.",
        "identity_prompt": "May I confirm your name, mobile number, and age?",
        "respondent_source": "Is the participant answering alone, with caregiver help, or is a caregiver answering for them?",
        "average_pain_prompt": "Thinking about the past 24 hours, what was the average joint pain from 0 to 10?",
        "current_pain_prompt": "And what number is the joint pain right now, from 0 to 10?",
        "not_caught": "I didn't catch that. Could you please say that again?",
        "already_complete": "This check-in is complete. You can start a new one if needed.",
        "continue": "Let's continue with your pain check-in.",
        "missing_identity": "Thank you. Could I also have your {missing}?",
        "thanks_name_pain": "Thank you, {name}. {pain_prompt}",
        "invalid_pain_score": "I need a number from 0 to 10.",
        "pain_location": "Where is the pain today?",
        "functional_impact": "How is it affecting you today? For example walking, stairs, sleep, or using your hands.",
        "comparison": "Is that better, worse, or about the same as usual?",
        "treatment": "Are you using anything for the pain now? Tablets, cream, injections, or therapy?",
        "side_effects": "Any side effects or new symptoms? For example stomach trouble, swelling, rash, dizziness, or breathing problems.",
        "side_effect_description": "Please briefly describe the symptom.",
        "side_effect_start": "When did it start?",
        "side_effect_status": "Is it still ongoing, or has it resolved?",
        "side_effect_severity": "Was it mild, moderate, severe, or are you not sure?",
        "medication_changed": "Did you reduce, pause, or stop any medicine because of this?",
        "doctor_contacted": "Did you contact a doctor or clinic about it?",
        "emergency_visit": "Did you go to emergency care or stay in hospital?",
        "red_flags": "Last safety check. Any chest pain, trouble breathing, black stools, vomiting blood, fainting, confusion, or fever with a hot swollen joint?",
        "complete": "Thank you. That's all for now. I'll prepare the doctor report.",
        "got_it_treatment": "Got it. Are you using anything for the pain now?",
        "ok_treatment": "Okay. Are you using anything for the pain now?",
        "thanks_function": "Thanks. How is it affecting you today?",
        "ok_function": "Okay. How is it affecting you today?",
        "clarify_score": "Sorry, please give a pain number from 0 to 10.",
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
    },
    "zh-CN": {
        "intro": (
            "您好，我是北京大学医学部医院的研究人员。"
            "这是研究原型，不是急救或治疗服务。"
            "想做一个简短的关节疼痛随访。"
        ),
        "hearing_check": "您能听清楚我说话吗？",
        "time_check": "现在方便继续吗？",
        "permission_check": "可以继续问几个随访问题吗？",
        "not_suitable_time": "好的，那这次先到这里。",
        "permission_declined": "好的，我会停止这次随访。",
        "identity_prompt": "先确认一下，您的姓名、手机号和年龄是多少？",
        "respondent_source": "现在是您本人回答，还是有家属帮忙，或者由家属代答？",
        "average_pain_prompt": "请回想过去24小时，平均关节疼痛是0到10分的几分？",
        "current_pain_prompt": "那现在这一刻，关节疼痛是0到10分的几分？",
        "not_caught": "不好意思，我没听清。请您再说一遍。",
        "already_complete": "这次随访已经完成了。如有需要，可以重新开始。",
        "continue": "我们继续做疼痛随访。",
        "missing_identity": "谢谢。还需要确认一下您的{missing}。",
        "thanks_name_pain": "谢谢，{name}。{pain_prompt}",
        "invalid_pain_score": "请说一个0到10的数字。",
        "pain_location": "今天主要哪里疼？",
        "functional_impact": "今天影响您做什么事？比如走路、上下楼、睡觉，或者用手。",
        "comparison": "和您平时相比，是轻了、重了，还是差不多？",
        "treatment": "现在有用什么止痛办法吗？比如药片、药膏、针剂，或者康复治疗。",
        "side_effects": "有没有不舒服或新的症状？比如胃不舒服、肿胀、皮疹、头晕，或者喘不上气。",
        "side_effect_description": "请简单说一下是什么不舒服。",
        "side_effect_start": "大概什么时候开始的？",
        "side_effect_status": "现在还在持续，还是已经好了？",
        "side_effect_severity": "程度是轻度、中度、重度，还是不确定？",
        "medication_changed": "因为这个情况，有没有减少、暂停或停止用药？",
        "doctor_contacted": "有没有联系医生或门诊？",
        "emergency_visit": "有没有去急诊，或者住院？",
        "red_flags": "最后确认安全问题。有没有胸痛、喘不上气、黑便、吐血、晕倒、意识混乱，或者关节又红又热还发烧？",
        "complete": "谢谢。今天先问到这里。我会整理给医生的报告。",
        "got_it_treatment": "明白了。现在有用什么止痛办法吗？",
        "ok_treatment": "好的。现在有用什么止痛办法吗？",
        "thanks_function": "谢谢。今天影响您做什么事？",
        "ok_function": "好的。今天影响您做什么事？",
        "clarify_score": "不好意思，请说一个0到10的疼痛数字。",
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
