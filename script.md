# OA Home Pain Check-in Assistant Script

This document summarizes the patient-facing OA check-in script, its clinical purpose, and the safety escalation rule. The running app keeps deterministic validation and red-flag rules as the source of truth; optional AI voice layers may make wording more conversational, but must preserve the clinical meaning, numbers, and urgent-care instructions.

## Scope

- Product: OA Home Pain Check-in Assistant
- Use case: short home monitoring check-in for suspected or diagnosed osteoarthritis-related joint pain
- Languages: English and Simplified Chinese
- Role: monitoring assistant only
- Not in scope: diagnosis, medication changes, prescribing, emergency-service replacement, or unsupervised clinical decision-making

## Core Assistant Rule

The assistant conducts a short, calm, medical-professional check-in. It asks one question at a time, records pain and symptom information, flags urgent symptoms, and prepares a structured doctor report. It does not diagnose, prescribe, or change treatment.

## Standard Flow

| Step                              | Clinical purpose                                                                         | English patient-facing line                                                                                                                                                                                  | Chinese patient-facing line                                                                                                    |
| --------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| 1. Introduction                   | Introduce the research check-in and disclose prototype limitations                       | Hello, I'm calling from the research team for a short joint pain check-in. This is a research prototype, not an emergency or treatment service. Before we start, I just need to make sure the call is clear. | 您好，这里是北京大学研究团队，想做一个简短的关节疼痛随访。这是研究原型，不是急救或治疗服务。开始前，我先确认一下通话是否清楚。 |
| 2. Hearing check                  | Confirm the participant can hear clearly                                                 | Can you hear me clearly?                                                                                                                                                                                     | 您能听清楚我说话吗？                                                                                                           |
| 3. Time check                     | Confirm this is a suitable time                                                          | Is now a good time to continue?                                                                                                                                                                              | 现在方便继续吗？                                                                                                               |
| 4. Permission                     | Obtain permission to ask follow-up questions                                             | Would it be okay if I ask a few follow-up questions now?                                                                                                                                                     | 如果您现在方便，我可以继续问几个随访问题吗？                                                                                   |
| 5. Identity                       | Collect name, mobile number, and age                                                     | Could I confirm your name, mobile number, and age?                                                                                                                                                           | 我先确认一下，您的姓名、手机号和年龄是多少？                                                                                   |
| 6. Respondent source              | Record whether answers are independent, assisted, or proxy                               | Just to record this correctly, are you answering by yourself, answering with help from a caregiver, or is a caregiver answering for you?                                                                     | 为了记录准确，我想确认一下：现在是您本人自己回答，家属在旁边帮忙，还是由家属代您回答？                                         |
| 7. Average pain                   | Estimate average joint pain over the past 24 hours through guided 0-10 anchor comparison | [Pain-Score Calibration Subscript](#pain-score-calibration-subscript)                                                                                                                                         | [Pain-Score Calibration Subscript](#pain-score-calibration-subscript)                                                           |
| 8. Current pain                   | Estimate current joint pain through guided 0-10 anchor comparison                        | [Pain-Score Calibration Subscript](#pain-score-calibration-subscript)                                                                                                                                         | [Pain-Score Calibration Subscript](#pain-score-calibration-subscript)                                                           |
| 9. Pain location                  | Collect main pain location today                                                         | Where are you feeling the pain today?                                                                                                                                                                        | 今天主要是哪个部位疼？                                                                                                         |
| 10. Functional impact             | Contextualize pain score with daily function                                             | How is it affecting you today? For example walking, stairs, sleep, or using your hands.                                                                                                                      | 今天影响您做什么事？比如走路、上下楼、睡觉，或者用手。                                                                         |
| 11. Usual comparison              | Compare today's pain with usual pain                                                     | Compared with your usual pain, is this better, worse, or about the same?                                                                                                                                     | 和您平时相比，这次是轻一些、重一些，还是差不多？                                                                               |
| 12. Treatment context             | Record current pain treatments or none                                                   | Are you using anything for the pain at the moment, such as tablets, cream, injections, or therapy?                                                                                                           | 您现在有没有用什么止痛办法？比如药片、药膏、针剂，或者康复治疗。                                                               |
| 13. Side effects and new symptoms | Screen for side effects, new symptoms, and possible urgent symptoms                      | Have you had any side effects or new symptoms, such as stomach trouble, swelling, rash, dizziness, or breathing problems?                                                                                    | 最近有没有不舒服或新的症状？比如胃不舒服、肿胀、皮疹、头晕，或者喘不上气。                                                     |
| 14. Red-flag safety check         | Screen for urgent symptoms requiring escalation                                          | Last safety check. Have you had chest pain, trouble breathing, black stools, vomiting blood, fainting, confusion, or fever with a hot swollen joint?                                                         | 最后确认几个安全问题。有没有胸痛、喘不上气、黑便、吐血、晕倒、意识混乱，或者关节又红又热还发烧？                               |
| 15. Closing                       | End the check-in and prepare report                                                      | Thank you. That's all for now. I'll prepare the doctor report.                                                                                                                                               | 谢谢。今天先问到这里。我会整理给医生的报告。                                                                                   |

## Conditional Lines

| Situation                          | English line                                                  | Chinese line                                   |
| ---------------------------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| Participant is not available       | No problem. We can stop here for now.                         | 好的，那这次先到这里。                         |
| Participant declines permission    | No problem. I will stop the check-in now.                     | 好的，我会停止这次随访。                       |
| Assistant did not catch the answer | I didn't catch that. Could you please say that again?         | 不好意思，我没听清。请您再说一遍。             |
| Missing identity field             | Thank you. Could I also have your name / mobile number / age? | 谢谢。还需要确认一下您的姓名 / 手机号 / 年龄。 |
| Invalid pain score                 | For this question, I need a number from 0 to 10.              | 这个问题需要记录一个0到10的数字。              |
| Check-in already complete          | This check-in is complete. You can start a new one if needed. | 这次随访已经完成了。如有需要，可以重新开始。   |

## Side-Effect Detail Subscript

If the participant reports side effects, new symptoms, or uncertainty, the assistant asks follow-up questions before the final red-flag safety check.

| Step                | Clinical purpose                                        | English line                                                      | Chinese line                                 |
| ------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------- |
| Symptom description | Collect a brief description                             | Could you briefly describe what you noticed?                      | 能简单说一下您注意到的症状吗？               |
| Start time          | Collect when symptom started                            | About when did it start?                                          | 大概什么时候开始的？                         |
| Current status      | Record whether ongoing or resolved                      | Is it still happening now, or has it resolved?                    | 现在还在持续吗，还是已经好了？               |
| Severity            | Record mild, moderate, severe, or unsure                | Would you say it was mild, moderate, severe, or are you not sure? | 您觉得程度是轻度、中度、重度，还是不太确定？ |
| Medication changed  | Record whether medicine was reduced, paused, or stopped | Because of this, did you reduce, pause, or stop any medicine?     | 因为这个情况，您有没有减少、暂停或停止用药？ |
| Doctor contacted    | Record whether clinician was contacted                  | Did you contact a doctor or clinic about it?                      | 有没有联系医生或门诊？                       |
| Emergency visit     | Record emergency care or hospitalization                | Did you need emergency care or a hospital stay?                   | 有没有因此去急诊，或者住院？                 |

## Pain-Score Calibration Subscript

The app now presents pain scoring through binary comparisons against concrete OA pain descriptions. If a participant directly gives a valid 0-10 number, the app can still accept it as a direct numeric override.

Opening calibration prompt:

| Pain period                | English                                                                                                                                                                                   | Chinese                                                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Average pain over past day | To record your average pain over the past day more accurately, please compare two descriptions. Is it closer to 5 or below: no joint pain, or 6 or above: the worst pain you can imagine? | 为了更准确记录过去一天的平均疼痛，请比较两个描述。它更接近5分以下：没有关节疼痛，还是6分以上：能想象到的最严重疼痛？ |
| Current pain               | To record your pain right now more accurately, please compare two descriptions. Is it closer to 5 or below: no joint pain, or 6 or above: the worst pain you can imagine?                 | 为了更准确记录现在这一刻的疼痛，请比较两个描述。它更接近5分以下：没有关节疼痛，还是6分以上：能想象到的最严重疼痛？   |

Pain anchors:

| Score | English anchor                                             | Chinese anchor                       |
| ----- | ---------------------------------------------------------- | ------------------------------------ |
| 0     | no joint pain                                              | 没有关节疼痛                         |
| 1     | very mild discomfort that is easy to ignore                | 很轻微的不适，基本可以忽略           |
| 2     | mild pain you notice, but it does not slow you down        | 能感觉到疼，但基本不影响活动         |
| 3     | mild pain that makes you a little careful with movement    | 轻度疼痛，活动时会稍微注意           |
| 4     | moderate pain that slows walking, stairs, or hand use      | 中等疼痛，会让走路、上下楼或用手变慢 |
| 5     | moderate pain that interrupts some daily tasks             | 中等疼痛，会影响一部分日常事情       |
| 6     | strong pain that makes normal activities clearly difficult | 较明显的疼痛，正常活动会比较困难     |
| 7     | severe pain that limits activity and is hard to ignore     | 较重疼痛，明显限制活动，很难忽略     |
| 8     | very severe pain; moving or resting is difficult           | 很重的疼痛，活动或休息都很困难       |
| 9     | extreme pain; you can barely do normal activities          | 极重疼痛，几乎难以进行正常活动       |
| 10    | the worst pain you can imagine                             | 能想象到的最严重疼痛                 |

Clarification if the comparison answer is unclear:

| English                                                                                                                                 | Chinese                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| To record the 0 to 10 score, please tell me whether it is closer to the first, milder description, or the second, stronger description. | 为了记录0到10分，请告诉我更接近前一个较轻的描述，还是后一个较重的描述。 |

Final calibrated score line:

| English                                                      | Chinese                               |
| ------------------------------------------------------------ | ------------------------------------- |
| I'll record that as [score] out of 10, closest to: [anchor]. | 我会记录为[score]分，接近：[anchor]。 |

## Urgent Escalation Rule

If a severe red flag is detected at any point, the assistant stops normal progression, advises urgent care, and flags the report.

Escalation message:

| English                                                                                                                                                                                                             | Chinese                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| I'm concerned about that. I can't diagnose it by phone, but it may need urgent care. Please call emergency services or seek urgent medical help now. If you are alone, please call someone nearby to stay with you. | 这个情况我比较担心。电话里不能诊断，但可能需要尽快就医。请现在联系急救或尽快去急诊。如果您一个人在家，请马上联系家人或身边的人陪您。 |

Red-flag categories currently screened:

- Chest pain
- Trouble breathing
- Stroke-like symptoms
- Severe allergic reaction
- Vomiting blood
- Black or bloody stools
- Fainting or severe dizziness
- Confusion
- Fever with a hot swollen joint
- New inability to stand, walk, or bear weight after fall, injury, trauma, or accident
- Severe symptoms after injection or treatment

## Non-Urgent Symptom Categories Tracked

These symptoms are recorded for the doctor report and follow-up review. They do not automatically trigger emergency escalation unless paired with a red flag or severe context.

- Stomach pain or heartburn
- Nausea
- Leg, ankle, or foot swelling
- Reduced urination
- Rash or skin irritation
- Constipation
- Drowsiness
- Yellow skin or eyes
- Dark urine
- Unusual bruising or bleeding

## Report Output

At the end of the check-in, the assistant prepares a structured doctor report containing:

- Patient identity
- Call metadata
- Pain assessment
- Side effects or symptoms reported
- Urgent red flags
- Summary for doctor
- Suggested follow-up priority
- Limitations

## Presentation Note

For demos, this script can be presented as the controlled clinical content of the assistant. The live voice experience may sound more natural because the app can use an AI voice layer for conversational delivery, but the clinical state machine owns the required questions, validation, escalation, and report generation.