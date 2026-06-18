# Project Requirement Document: Osteoarthritis Pain Inquiry & Management Voice Assistant

  Product Name: OA Home Pain Check-in Assistant
  Prototype Version: v0.1
  Primary Mode: Voice conversation
  Primary User: Older adults or adults with suspected, diagnosed, moderate, or severe osteoarthritis using the app at home
  Primary Output: A concise clinical report for the doctor after each call

  ## 1. Product Summary

  The OA Home Pain Check-in Assistant is a voice-based home monitoring tool for people experiencing osteoarthritis-related joint pain. The prototype conducts a
  short, friendly, medically appropriate check-in that:

  1. Confirms the user’s identity with minimal burden.
  2. Assesses the user’s pain using a 0-10 pain scale, supported by functional anchors to reduce reporting bias.
  3. Asks about side effects or urgent symptoms related to osteoarthritis, common OA medications, injections, and general health red flags.
  4. Advises the user to seek urgent medical help if severe red flags are reported.
  5. Generates a structured report for the doctor.

  The assistant does not diagnose osteoarthritis, change medications, prescribe treatment, or replace emergency services. It supports monitoring and escalation.

  Clinical grounding: osteoarthritis management commonly includes lifestyle measures, exercise, weight management, pain medicines, topical or oral NSAIDs,
  opioids in limited cases, capsaicin cream, steroid injections, supportive devices, and in some cases surgery. NICE states OA guidance covers diagnosis,
  assessment, non-surgical management, information/support, pharmacological and non-pharmacological care, follow-up, and referral decisions. NHS describes OA
  treatment as symptom relief through lifestyle measures, medication, and supportive therapies, with surgery considered in selected cases. Sources: NICE NG226
  and NHS OA treatment guidance.

  ## 2. Goals

  The prototype must achieve these goals:

  - Provide a short, comfortable, elder-friendly voice check-in.
  - Collect a more clinically useful pain score than “What is your pain from 0 to 10?” alone.
  - Identify urgent severe side effects or red-flag symptoms.
  - Advise immediate care-seeking when urgent symptoms are present.
  - Produce a doctor-readable report with pain score, side effects, red flags, and recommended follow-up urgency.
  - Use a warm, calm, friendly medical-professional tone.

  ## 3. Non-Goals

  The prototype will not:

  - Diagnose OA or distinguish OA from rheumatoid arthritis, gout, infection, fracture, cancer, or other causes.
  - Recommend medication changes.
  - Provide individualized dosing advice.
  - Replace emergency services.
  - Perform full medication reconciliation.
  - Manage chronic disease beyond the brief pain and side-effect check-in.
  - Provide legal medical documentation as an official clinical note.

  ## 4. Target Users

  Primary users:

  - Older adults with suspected or diagnosed osteoarthritis.
  - Patients with chronic knee, hip, hand, spine, shoulder, or foot pain.
  - Patients recovering from or monitoring treatment such as pain medicines, topical medicines, steroid injections, physiotherapy, or joint procedures.
  - Users may have hearing issues, memory issues, low health literacy, or discomfort describing symptoms.

  Design implications:

  - Use short questions.
  - Avoid medical jargon unless explained.
  - Ask one thing at a time.
  - Confirm important answers gently.
  - Allow “I’m not sure.”
  - Avoid blame or pressure.
  - Make identity confirmation quick.

  ## 5. Core Conversation Flow

  ### 5.1 Opening Tone

  The assistant should sound like a friendly medical professional: calm, respectful, concise, and reassuring without overpromising.

  Example opening:

  “Hello, I’m your osteoarthritis pain check-in assistant. I’ll ask a few quick questions about your pain today and whether you’ve had any concerning symptoms
  or side effects. This should only take a few minutes, and I’ll prepare a short report for your doctor.”

  ### 5.2 Identity Confirmation

  Required fields:

  - Name
  - Handphone number
  - Age

  The assistant should reduce burden by asking naturally:

  “Before we begin, may I confirm your name, mobile number, and age?”

  If user gives partial information, ask only for the missing field.

  Identity confirmation should not become an authentication barrier in this prototype. If the user cannot remember or refuses a field, proceed but mark the
  report as “identity incomplete.”

  ### 5.3 Pain Assessment

  The assistant should use the 0-10 Numeric Rating Scale, where:

  - 0 = no pain
  - 1-3 = mild pain
  - 4-6 = moderate pain
  - 7-10 = severe pain

  However, because simple 0-10 scoring is vulnerable to user bias, mood, memory error, cultural interpretation, and different personal thresholds, the assistant
  must use a more scientifically grounded approach:

  1. Ask for the numeric score.
  2. Anchor the score to function.
  3. Ask about location.
  4. Ask whether pain is better, worse, or the same compared with the user’s usual pain.
  5. Confirm unusually high or inconsistent responses.

  Example:

  “On a scale from 0 to 10, where 0 means no pain and 10 means the worst pain you can imagine, what number best describes your joint pain right now?”

  Then:

  “To make sure I understand the number correctly, how much is the pain affecting what you can do today? For example, walking, climbing stairs, using your
  hands, sleeping, or getting dressed.”

  Functional anchors:

  - 0: no pain
  - 1-3: noticeable but can do usual activities
  - 4-6: interferes with activities, walking, sleep, or household tasks
  - 7-8: hard to do normal activities or needs significant rest/help
  - 9-10: unbearable, unable to function, or feels like an emergency

  If user says “10” but reports normal function, the assistant should not challenge them. It should clarify:

  “Thank you. Just to help your doctor understand, would you say this pain is stopping you from normal activities today, or is it severe but still manageable?”

  ### 5.4 Side Effects and Red Flags

  The assistant should ask about side effects in a comfortable, non-alarming way.

  Example:

  “Some people with joint pain or arthritis treatments notice side effects or new symptoms. I’ll ask about a few important ones. You can simply say yes, no, or
  not sure.”

  The assistant should cover common OA treatment-related concerns, including:

  - NSAIDs such as ibuprofen, naproxen, diclofenac:
      - stomach pain, heartburn, nausea
      - black stools or blood in stool
      - vomiting blood or coffee-ground-like vomit
      - chest pain
      - shortness of breath
      - weakness on one side
      - slurred speech
      - swelling of legs, ankles, or feet
      - reduced urination
      - rash, hives, facial/lip/tongue/throat swelling

  - Acetaminophen/paracetamol:
      - taking more than directed
      - yellow skin or eyes
      - dark urine
      - upper belly pain
      - unusual bleeding or bruising

  - Opioids such as codeine or tramadol, if applicable:
      - severe drowsiness
      - confusion
      - slow or difficult breathing
      - severe constipation

  - Steroid injections or steroid medicines:
      - fever
      - signs of infection
      - severe worsening joint pain after injection
      - mood changes
      - high blood sugar symptoms if diabetic

  - Topical treatments:
      - severe rash, blistering, swelling, or allergic reaction

  - General urgent symptoms:
      - chest pain
      - trouble breathing
      - signs of stroke
      - severe allergic reaction
      - vomiting blood
      - black/tarry stools
      - fainting or severe dizziness
      - confusion
      - fever with hot, swollen, very painful joint
      - new inability to bear weight after injury or fall

  MedlinePlus notes urgent NSAID warning symptoms such as chest pain, shortness of breath, one-sided weakness, slurred speech, bloody vomit, blood in stool, or
  black/tarry stools. MedlinePlus also lists acetaminophen overdose/liver warning symptoms such as yellowing skin/eyes, upper belly pain, dark urine, pale
  stools, severe rash/swelling, or breathing/swallowing difficulty. NHS notes steroids can increase infection risk and cause other serious effects, especially
  at higher dose or longer duration.

  ## 6. Red Flag Escalation Behavior

  If any severe urgent red flag is detected, the assistant must:

  1. Stop routine questioning unless it is necessary to clarify urgency.
  2. Clearly advise urgent medical care.
  3. Avoid diagnosing the cause.
  4. Add a prominent red flag section to the doctor report.
  5. If available in the final product, trigger emergency contact or care-team alert; for this prototype, only verbal advice and report flagging are required.

  Example escalation language:

  “I’m concerned about what you just described. I can’t diagnose this, but symptoms like that can need urgent medical attention. Please contact emergency
  services or seek urgent medical care now. If you are alone, please call a family member, caregiver, or neighbor to stay with you while you get help.”

  For non-urgent side effects:

  “Thank you for telling me. I’ll include that in your doctor’s report so they can review it.”

  ## 7. Conversation Style Requirements

  The assistant must:

  - Speak warmly and calmly.
  - Use plain language.
  - Ask one question at a time.
  - Avoid long explanations.
  - Avoid sounding robotic, rushed, or alarmist.
  - Respect uncertainty.
  - Confirm severe symptoms.
  - Avoid giving false reassurance.
  - Avoid medication instructions beyond “seek urgent care” or “speak with your doctor/pharmacist,” unless explicitly pre-approved.

  Preferred phrases:

  - “Thank you, that helps.”
  - “Take your time.”
  - “You can answer yes, no, or not sure.”
  - “I’ll make sure your doctor sees that.”
  - “I’m concerned about that symptom.”

  Avoid:

  - “You definitely have…”
  - “You should stop/start/change your medication…”
  - “That is normal, don’t worry.”
  - “This is not serious.”

  ## 8. Doctor Report Requirements

  The report must be structured, brief, and easy to scan.

  ### Report Template

  OA Home Pain Check-in Report

  Patient Identity

  - Name:
  - Mobile number:
  - Age:
  - Identity status: complete / incomplete

  Call Metadata

  - Date/time:
  - Conversation type: Home monitoring OA pain check-in
  - Assistant version: v0.1

  Pain Assessment

  - Pain score: X/10
  - Scale used: 0-10 Numeric Rating Scale with functional anchoring
  - Pain location(s):
  - Functional impact:
  - Compared with usual pain: better / same / worse / unknown
  - Patient’s own words:

  Side Effects / Symptoms Reported

  - Reported symptoms:
  - Medication or treatment context, if mentioned:
  - Non-urgent concerns:

  Urgent Red Flags

  - Red flag present: yes / no / uncertain
  - Red flag symptom(s):
  - Action advised: urgent medical care / emergency services / contact caregiver / no urgent escalation

  Summary for Doctor

  - 2-4 sentence summary of the call.
  - Highlight changes in pain, functional limitation, and urgent symptoms.

  Suggested Follow-up Priority

  - Emergency: severe red flag reported
  - High priority: severe pain score, major functional decline, or concerning non-emergency symptoms
  - Routine: stable pain and no red flags

  Limitations

  - Voice self-report only.
  - No physical exam performed.
  - No diagnosis or medication adjustment made.

  ## 9. Prompt Specification for the Voice Assistant

  The system prompt should instruct the assistant as follows:

  “You are a friendly medical-professional voice assistant for home monitoring of suspected or diagnosed osteoarthritis pain. Your job is to conduct a short
  check-in, confirm basic identity, assess pain using a 0-10 Numeric Rating Scale supported by functional questions, ask about side effects and urgent red
  flags, advise urgent care when severe red flags are reported, and generate a structured report for the doctor. You do not diagnose, prescribe, or change
  medication. Use calm, plain language suitable for older adults. Ask one question at a time. If the user reports chest pain, trouble breathing, stroke-like
  symptoms, severe allergic reaction, vomiting blood, black stools, confusion, fainting, severe dizziness, fever with a hot swollen joint, or severe symptoms
  after treatment, advise urgent medical attention and flag the report.”

  ## 10. Acceptance Criteria

  The prototype is successful if:

  - It confirms name, mobile number, and age without making the user repeat unnecessary information.
  - It collects a 0-10 pain score.
  - It asks at least one functional-impact question to contextualize the pain score.
  - It asks about side effects and severe red flags in plain language.
  - It escalates urgent symptoms verbally and in the report.
  - It produces a structured doctor report.
  - It does not diagnose, prescribe, or change treatment.
  - It maintains a friendly, calm, medically appropriate tone.

  ## 11. Safety and Compliance Notes

  - This product is a monitoring assistant, not a medical device diagnosis engine in the prototype stage.
  - Emergency advice should be conservative.
  - All urgent symptoms should be treated as self-reported and flagged clearly.
  - The app should include privacy and consent handling before real deployment.
  - If deployed clinically, it may require review for medical device, HIPAA/privacy, local health-data, and clinical governance requirements.

  ## 12.App Development & Technical Architecture Notes

  ### Prototype Hosting Target

  The prototype will run locally on the developer’s machine. It should be lightweight, low-cost, and designed so that future expansion to a hosted web
  app, mobile app, or clinical dashboard is possible without rewriting the core clinical logic.

  ### Recommended Stack

  **Backend**
  - Python
  - FastAPI
  - Local HTTP API for conversation state, safety checks, and report generation

  **Frontend**
  - Browser-based local UI
  - Plain HTML/CSS/JavaScript or lightweight React
  - Browser microphone input and speech output for the earliest prototype

  **Local Model**
  - Existing local model path:
  ```text
  /home/lawrencelcty/huggingface/models/Qwen/Qwen3-4B-Instruct-2507-FP8
  ```

  The model should be invoked only when useful, not treated as the sole decision-making engine.

  ### Model Usage Policy

  The local Qwen model may be used for:

  - Rephrasing assistant messages in a friendly medical-professional tone
  - Handling natural language variation in user responses
  - Summarizing the completed conversation
  - Drafting the final doctor report from structured data
  - Making the conversation feel smoother and less scripted

  The local Qwen model must not be the sole authority for:

  - Red-flag detection
  - Emergency escalation
  - Required question completion
  - Pain scale interpretation
  - Clinical safety decisions
  - Medication advice
  - Diagnosis or treatment recommendations

  Clinical safety logic should be deterministic and rule-based wherever possible.

  ### Core Architecture Principle

  The app should separate responsibilities clearly:

  Voice UI
    -> captures user speech and displays transcript

  Conversation State Machine
    -> determines the next required question

  Clinical Rules Layer
    -> detects red flags and escalation conditions

  Local LLM Layer
    -> improves wording, summaries, and report phrasing

  Report Generator
    -> produces doctor-readable structured output

  The app should remain functional even if the local LLM is unavailable. In that case, it should fall back to scripted prompts and template-based report
  generation.

  ### Speech Handling

  For the first local prototype, the preferred approach is:

  - Browser Web Speech API for speech-to-text
  - Browser speech synthesis for text-to-speech

  This avoids running separate local speech recognition and voice synthesis models during the initial prototype.

  Future upgrade path:

  - Add faster-whisper or another local ASR model if browser transcription quality is insufficient.
  - Add a dedicated local or cloud TTS engine if browser speech sounds unnatural or inconsistent.

  ### Lightweight Operation Strategy

  Because the local environment has approximately 4-8GB spare RAM and an RTX 4050 laptop GPU, the app should avoid running multiple large models
  simultaneously.

  Preferred strategy:

  - Keep the clinical flow and safety checks in normal Python code.
  - Use structured data for all captured answers.
  - Invoke the local LLM only at controlled points, such as:
      - after user input needs interpretation
      - when generating a friendlier assistant utterance
      - when producing the final report

  - Avoid long context windows unless needed.
  - Prefer short prompts with structured JSON-like inputs.
  - Cache or template repeated assistant messages where possible.

  ### Suggested Backend Modules

  app/
    main.py              # FastAPI app and routes
    conversation.py      # conversation state machine
    clinical_rules.py    # red flag and safety logic
    pain_scale.py        # pain score validation and functional anchoring
    report.py            # structured doctor report generation
    llm.py               # local Qwen invocation wrapper
    schemas.py           # request/response/data models
  static/
    index.html
    app.js
    styles.css

  ### Suggested Development Order

  1. Build the text-based conversation state machine.
  2. Add deterministic red-flag detection.
  3. Add structured report generation.
  4. Add local browser UI.
  5. Add browser speech input/output.
  6. Add optional local Qwen invocation for response polishing and report drafting.
  7. Add fallback behavior when the model is unavailable.
  8. Test severe red-flag scenarios and report output.

  ### Local Model Integration Requirement

  The local model wrapper should be isolated behind a small interface, for example:

  generate_assistant_reply(context) -> string
  summarize_for_report(structured_call_data) -> string

  The rest of the application should not depend directly on Qwen-specific APIs. This will allow future replacement with:

  - another Hugging Face model
  - Ollama
  - llama.cpp
  - a hosted LLM API
  - no LLM at all

  ### Safety Requirement

  The app must always prioritize deterministic clinical safety checks over local model output. If the model-generated response conflicts with the rule-
  based red-flag logic, the rule-based logic wins.

  Example:

  If the user reports “I have chest pain and trouble breathing,” the app must advise urgent medical care and flag the doctor report, even if the local
  model produces a softer or non-urgent response.

  ### Data Handling Notes

  For the local prototype:

  - Store conversation state in memory by default.
  - Optionally save final reports as local JSON or Markdown files.
  - Avoid collecting unnecessary personal data.
  - Do not send patient data to external services unless explicitly enabled later.

  Future production versions should include:

  - encryption at rest
  - access control
  - audit logs
  - consent flow
  - healthcare privacy compliance review
  - clinician-facing dashboard

  ## Sources Used

  - NICE Guideline NG226, Osteoarthritis in over 16s: diagnosis and management: https://www.nice.org.uk/guidance/ng226
  - NHS, Osteoarthritis - Treatment and support: https://www.nhs.uk/conditions/osteoarthritis/treatment/
  - NHS, Osteoarthritis - Symptoms: https://www.nhs.uk/conditions/osteoarthritis/symptoms/
  - MedlinePlus, Naproxen Drug Information: https://medlineplus.gov/druginfo/meds/a681029.html
  - MedlinePlus, Ibuprofen Drug Information: https://medlineplus.gov/druginfo/meds/a682159.html
  - MedlinePlus, Acetaminophen Drug Information: https://medlineplus.gov/druginfo/meds/a681004.html
  - NHS, Steroids: https://www.nhs.uk/medicines/steroids/
rea