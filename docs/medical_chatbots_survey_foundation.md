# Medical Chatbots: A Comprehensive Survey Foundation for AI Chatbots in Healthcare Applications

Current as of 2026-07-02. Scope: papers from 2021-07-02 to 2026-07-02, with older datasets mentioned only when they are used by in-scope papers. This is a survey-paper foundation, not a final PRISMA-certified systematic review. I did not infer DOI, citation-count, GitHub, or project-page fields when they were not confirmed from accessible sources during this pass. `NR` means not reported or not confirmed in this pass; `N/A` means not applicable.

## 1. Introduction

Medical chatbot research shifted sharply in the last five years. Before 2023, most deployed healthcare chatbots were scripted, retrieval-based, or intent-classification systems used for mental health, behavior change, triage, and patient education. Since 2023, the field has been dominated by large language models (LLMs), medical instruction tuning, retrieval-augmented generation (RAG), and multimodal medical assistants. The result is a fragmented literature: some papers evaluate general chatbots such as ChatGPT or GPT-4 on exams and patient questions, some build domain-specific medical LLMs, some introduce RAG or knowledge-graph grounding, and others build vision-language assistants for radiology, pathology, biomedicine, or mental health.

The central lesson is that medical chatbot capability is no longer defined only by natural-language fluency. Useful systems require clinical grounding, uncertainty handling, safety constraints, personalization, source traceability, and human evaluation. Exam accuracy and benchmark wins are insufficient evidence for clinical deployment.

## 2. Background

Medical chatbots can be understood along three axes.

1. Interaction style: scripted, retrieval-based, generative single-turn QA, multi-turn consultation, agentic diagnostic dialogue, or multimodal conversation.
2. Knowledge source: parametric model memory, domain fine-tuning, prompt engineering, RAG over documents/EHR/guidelines, medical knowledge graphs, or clinician-authored rules.
3. Clinical role: patient education, symptom triage, clinical decision support, mental health support, medical education, radiology/pathology assistance, hospital workflow automation, or specialty-specific counseling.

The literature repeatedly shows that model scale and instruction tuning improve benchmark performance, but do not solve clinical safety. Fine-tuning improves domain style and coverage, but may copy unsafe online-consultation behavior. RAG improves currency and traceability, but can degrade answers when retrieval is irrelevant. Multimodal models enable image-grounded chat, but remain vulnerable to weak visual grounding and hallucinated findings.

## 3. Research Methodology

### 3.1 Search Strategy

Searches combined the user-specified terms with venue and system names. Example query families:

- `medical chatbot`, `healthcare chatbot`, `clinical chatbot`, `patient chatbot`, `medical conversational AI`
- `LLM healthcare`, `LLM medical assistant`, `medical large language model`, `clinical conversational agent`
- `medical dialogue system`, `medical consultation chatbot`, `diagnostic chatbot`, `clinical decision support chatbot`
- `medical RAG`, `retrieval augmented generation medical QA`, `knowledge graph medical copilot`
- `multimodal medical chatbot`, `vision-language medical assistant`, `radiology chatbot`, `pathology copilot`
- `mental health chatbot`, `AI therapist`, `LLM mental health support`

Sources prioritized: Nature, Nature Medicine, npj Digital Medicine, The Lancet family, JAMA/JMIR/Radiology where relevant, ACL/EMNLP/Findings, IEEE/ACM, NeurIPS/ICLR/ICML/AAAI where relevant, and arXiv only when the work is influential, widely used, or releases models/datasets.

### 3.2 Inclusion Criteria

- Published or posted between 2021-07-02 and 2026-07-02.
- Directly concerned with medical, clinical, biomedical, mental-health, patient-facing, or healthcare-workflow conversational agents.
- Includes a model, benchmark, system, clinical evaluation, or systematic evidence relevant to medical chatbots.
- ArXiv included only for influential open-source medical LLM, RAG, or multimodal chatbot systems.

### 3.3 Exclusion Criteria

- General conversational AI with only passing healthcare mention.
- Opinion/editorial-only papers.
- Short abstracts without technical or evaluation detail, unless central to a widely used system.
- Papers outside the five-year window, except as legacy datasets or historical context.

### 3.4 Paper Selection Process

This pass used a curated scoping workflow rather than a full PRISMA process. The artifact below identifies a high-signal core corpus and records unconfirmed bibliographic fields explicitly. A publishable survey should next convert this into a spreadsheet, run duplicate removal across PubMed, ACM DL, IEEE Xplore, ACL Anthology, Semantic Scholar, Scopus/Web of Science, and arXiv, then conduct two-reviewer inclusion adjudication.

### 3.5 Research Questions

RQ1. Research evolved from scripted/retrieval chatbots to LLM-based assistants in 2023, then to aligned medical LLMs, RAG, multimodal assistants, and clinical-style dialogue evaluation in 2024-2026.

RQ2. Major categories: scripted/retrieval intervention bots, medical QA chatbots, medical consultation LLMs, RAG-grounded assistants, diagnostic decision-support agents, mental-health chatbots, workflow copilots, and multimodal/vision-language assistants.

RQ3. Dominant architectures: intent/rule engines for older intervention bots; encoder-decoder/Transformer models for earlier dialogue; decoder-only LLMs for current text systems; LLaVA/OpenFlamingo-style vision-language architectures for multimodal systems; RAG plus dense retrieval/knowledge graphs for grounded systems.

RQ4. Common LLMs: GPT-3.5, GPT-4/GPT-4 class models, PaLM/Flan-PaLM/Med-PaLM, Gemini-family systems in later evaluations, LLaMA/Llama 2/Llama 3, Vicuna, ChatGLM, Mistral, OpenFlamingo, and domain derivatives such as HuatuoGPT, MedAlpaca, PMC-LLaMA, BioMistral, Med42, MEDITRON, Clinical Camel, and DISC-MedLLM.

RQ5. Common datasets: MedQA, MedMCQA, PubMedQA, MMLU clinical topics, LiveQA, MedicationQA, HealthSearchQA/MultiMedQA, DDXPlus, MIMIC-CXR, CheXpert, RadGraph, VQA-RAD, PathVQA, SLAKE, PMC-VQA, MultiMedBench, CheXbench/CheXinstruct, BianQueCorpus, Psych8k, PsyQA as legacy mental-health data, and AfriMed-QA.

RQ6. Metrics: accuracy, F1, AUROC, exact match, BLEU/ROUGE/METEOR/CIDEr, BERTScore, CheXpert/CheXbert, RadGraph, RadFact, GREEN, hallucination/factuality, helpfulness, harm, bias, empathy, OSCE-style human ratings, clinician preference, diagnosis accuracy, treatment specificity, usability, engagement, and clinical outcome measures such as PHQ-9/GAD-7.

RQ7. Systems differ by grounding, target user, medical domain, dialogue depth, modality, openness, and evaluation quality. A benchmark-only LLM is not equivalent to a patient chatbot.

RQ8. Strengths and weaknesses: general LLMs are broad but hallucinate; medical LLMs are specialized but data-limited; RAG improves traceability but depends on retrieval quality; multimodal systems broaden input but can hallucinate visual findings; rule/retrieval bots are safer in narrow workflows but brittle.

RQ9. Explored specialties: general medicine, primary care, emergency/triage, radiology, pathology, oncology, breast screening, pediatrics, toxicology, infectious disease/antimicrobial advice, mental health, chronic pain, medical education, biomedical research, Alzheimer's disease imaging, and traditional Chinese medicine.

RQ10. Gaps: real clinical validation, multilingual and low-resource coverage, safety under distribution shift, robust crisis handling, privacy-preserving personalization, source attribution, long-term memory, physician collaboration, regulatory readiness, bias evaluation, and standardized clinical-chatbot benchmarks.

## 4. Taxonomy of Medical Chatbots

| Taxon | Definition | Dominant architecture | Representative papers |
|---|---|---|---|
| T1 Scripted and retrieval intervention bots | Fixed flows, templates, intent classifiers, or retrieval responses for health behavior and mental health | Rules, NLU intent classification, retrieval response selection | Li et al. 2023 mental-health meta-analysis; older Woebot-style systems as context |
| T2 Medical QA chatbots | Answer medical exam, consumer, or clinician questions | Prompted LLMs, instruction tuning, self-consistency | Med-PaLM, Med-PaLM 2, GPT-4 medical challenge, ChatGPT USMLE studies |
| T3 Domain-fine-tuned medical LLMs | Open or closed LLMs adapted using medical corpora and instructions | Continued pretraining, SFT, LoRA/QLoRA, preference alignment | ChatDoctor, MedAlpaca, PMC-LLaMA, HuatuoGPT, Clinical Camel, MEDITRON, BioMistral, Med42 |
| T4 Multi-turn consultation chatbots | Systems optimized for patient-doctor style dialogue | SFT on consultations, self-play, chain of questioning, RLAIF/RLHF | AMIE, DISC-MedLLM, HuatuoGPT, BianQue, DoctorGLM |
| T5 RAG and knowledge-grounded assistants | Retrieve external evidence, guidelines, EHR cases, or KG facts before answering | Dense retrieval, reranking, KG reasoning, evidence filtering | ChatDoctor, MedRAG, RAG2, DERA, MIRAGE graph RAG |
| T6 Diagnostic and clinical decision-support agents | Produce differential diagnosis, management plan, or clinical reasoning | LLM agents, OSCE simulation, RAG, KG reasoning | AMIE, MedRAG, DERA, GPT-4 clinical evaluations |
| T7 Mental-health chatbots | Counseling, emotional support, CBT/psychoeducation, crisis response | Retrieval bots, generative LLMs, empathy fine-tuning | SoulChat, ChatCounselor, Mental-LLM, Therabot, Li et al. meta-analysis |
| T8 Specialty patient-education bots | Answer domain-specific patient questions | General LLMs or small domain bots | ChatGPT breast screening, toxicology, pediatrics, oncology evaluations |
| T9 Multimodal medical chatbots | Converse over text plus medical images, reports, pathology, genomics, molecules | VLMs, LLaVA-style projection, Flamingo-style cross-attention, multimodal LLMs | LLaVA-Med, Med-Flamingo, Med-PaLM M, XrayGPT, PathChat, CheXagent, MAIRA-2 |
| T10 Workflow copilots | Draft reports, summarize conversations, improve documentation, assist clinicians | LLMs, VLMs, multi-agent prompting, workflow evaluation | DERA, CheXagent, MAIRA-2, PathChat |

## 5. Survey of Existing Methods

### 5.1 From Rule-Based Chatbots to LLM Chatbots

The pre-LLM clinical chatbot literature emphasized safety by constraining behavior. Mental-health and behavior-change agents often used scripted CBT, retrieval libraries, check-ins, and mobile-app delivery. The 2023 npj Digital Medicine meta-analysis found most mental-health conversational agents in experimental studies were retrieval-based rather than truly generative; only a small subset used generative models. This safety-by-construction design reduces hallucination but limits personalization and open-ended reasoning.

LLM-based papers changed the field by demonstrating broad medical knowledge and interactive explanatory ability. Med-PaLM introduced MultiMedQA and a human-evaluation framework for consensus, comprehension, reasoning, harm, and bias. GPT-4 evaluations then showed that very large general LLMs could outperform earlier medical-specialized systems on exam-style tasks without medical fine-tuning. The tradeoff is clear: scale and instruction tuning increase capability, but they do not guarantee grounded, safe, clinically validated dialogue.

### 5.2 Medical QA and Patient Education

Medical QA chatbots dominate benchmark research because they are easy to score. MedQA, MedMCQA, PubMedQA, MMLU clinical topics, and MultiMedQA enabled rapid comparison across GPT-3.5, GPT-4, PaLM, Med-PaLM, LLaMA derivatives, and open medical LLMs. However, benchmark QA is only a weak proxy for clinical chatbot quality. It usually lacks longitudinal history-taking, ambiguity, patient preferences, missing data, time pressure, medico-legal constraints, and local guideline variation.

Patient education studies such as physician-vs-chatbot Reddit answers and specialty-specific ChatGPT evaluations highlight a recurrent pattern: LLM answers are often more complete and empathetic, but factual correctness, outdated advice, fabricated references, and lack of context remain serious risks.

### 5.3 Domain-Fine-Tuned Medical LLMs

Open-source medical LLMs pursued several adaptation recipes. ChatDoctor fine-tuned LLaMA on patient-doctor dialogue and added retrieval. MedAlpaca created a large instruction dataset for medical conversation. PMC-LLaMA injected PubMed Central and textbook knowledge through continued pretraining and instruction tuning. HuatuoGPT combined ChatGPT-distilled data with doctor data and RLAIF. Clinical Camel encoded knowledge through synthetic dialogue. MEDITRON scaled medical continued pretraining on Llama 2. BioMistral continued pretraining Mistral on PubMed Central and evaluated multilingual generalization. Med42-v2 used Llama 3 plus clinical fine-tuning and preference alignment.

These methods generally improve medical terminology, QA accuracy, and consultation style, but they inherit limitations from source data. Online consultation corpora may contain incomplete histories, non-standard advice, or cultural biases. Synthetic ChatGPT-distilled data can transfer teacher-model errors and style. Continued pretraining may improve knowledge but not alignment. Preference alignment improves response style but needs clinician-grounded reward criteria.

### 5.4 Multi-Turn Consultation and Diagnostic Agents

AMIE is a key shift from QA to diagnostic dialogue. It uses self-play and simulated patient interactions to train and evaluate history-taking, differential diagnosis, management reasoning, communication, and empathy in OSCE-like text consultations. BianQue targets the chain-of-questioning ability missing from single-turn health advice. DISC-MedLLM trains on knowledge-graph-derived data, reconstructed real-world dialogues, and human-guided preference rephrasing.

The important distinction is that diagnostic chatbots must ask the right next question before answering. Single-turn answer quality is not enough. However, AMIE-style evaluations still do not equal real clinical deployment because text chat with actors differs from clinical practice, physical examination, imaging, labs, time constraints, and accountability.

### 5.5 RAG and Knowledge-Grounded Chatbots

RAG is increasingly treated as a required component for medical chatbot safety. ChatDoctor uses self-directed information retrieval. MedRAG uses a diagnostic knowledge graph and EHR retrieval to distinguish similar diseases and propose follow-up questions. RAG2 uses LLM-generated rationales as retrieval queries, filters noisy evidence, and balances multiple biomedical corpora. DERA uses a dialog between LLM agents to improve medical conversation summarization and care-plan generation.

RAG is strongest when knowledge is curated, retrieval can be audited, and answer claims cite evidence. It is weakest when irrelevant documents are retrieved, sources conflict, or the generator treats retrieved text uncritically. Medical RAG therefore needs retrieval evaluation, source provenance, update policies, conflict resolution, and clinician-facing evidence presentation.

### 5.6 Mental-Health Chatbots

Mental-health chatbots have the strongest history of intervention trials but also the most severe safety sensitivities. The 2023 npj Digital Medicine meta-analysis reported significant reductions in depression and distress across AI-based conversational agents, with substantial heterogeneity and limited long-term evidence. Generative systems such as SoulChat and ChatCounselor fine-tune LLMs for empathy and counseling-like responses. Therabot provides stronger evidence because it is a randomized trial of a generative AI chatbot for mental health treatment.

The major risk is that empathic fluency can be mistaken for clinical competence. Crisis detection, suicidality handling, escalation to human care, privacy, dependency, and boundary management are unresolved.

### 5.7 Multimodal Medical Assistants

Multimodal medical chatbots emerged quickly after 2023. LLaVA-Med adapts LLaVA to biomedical figures using PubMed Central images and GPT-4-generated instructions. Med-Flamingo continues pretraining OpenFlamingo on medical image-text data for few-shot medical VQA. XrayGPT aligns a radiology image encoder with Vicuna for chest-radiograph conversation. Med-PaLM M and MultiMedBench broaden the scope to radiology, dermatology, genomics, mammography, and medical QA. PathChat targets pathology; CheXagent and MAIRA-2 target chest X-ray interpretation and report drafting.

The technical trend is clear: most systems connect a medical image encoder to a general LLM through adapters or cross-attention, then instruction-tune on image-text tasks. The clinical gap is equally clear: metrics such as BLEU and VQA accuracy are often insufficient, and models can hallucinate findings not present in the image. Grounded report generation and radiologist evaluation are stronger directions.

## 6. Comparative Analysis

### Table 1. Paper vs Medical Task

| Task | Representative papers |
|---|---|
| Medical exam QA | Med-PaLM, Med-PaLM 2, GPT-4 medical challenge, Kung et al., Gilson et al., MedMCQA, BioMistral, MEDITRON, Clinical Camel |
| Consumer/patient QA | Med-PaLM, ChatGPT physician-response study, ChatDoctor, HuatuoGPT, MedAlpaca |
| Multi-turn consultation | AMIE, DISC-MedLLM, BianQue, DoctorGLM, HuatuoGPT |
| Diagnostic support | AMIE, MedRAG, DERA, GPT-4 clinical challenge, M-ARC limitations paper |
| Mental health support | SoulChat, ChatCounselor, Mental-LLM, Therabot, Li et al. meta-analysis |
| Radiology VQA/reporting | LLaVA-Med, Med-Flamingo, XrayGPT, CheXagent, MAIRA-2, Med-PaLM M |
| Pathology copilot | PathChat |
| Biomedical multimodal discovery | BioMedGPT, MedBLIP, Med-PaLM M |
| RAG/evidence grounding | ChatDoctor, MedRAG, RAG2, DERA, MIRAGE graph RAG |

### Table 2. Paper vs Model and LLM

| Model family | Papers | Strength | Weakness |
|---|---|---|---|
| GPT-3.5/GPT-4 | GPT-4 medical challenge, DERA, ChatGPT USMLE, physician-response, specialty evaluations | Strong zero/few-shot reasoning and fluent explanation | Closed model, limited transparency, possible hallucination |
| PaLM/Med-PaLM | Med-PaLM, Med-PaLM 2, Med-PaLM M | Strong benchmark and human-evaluation framework | Mostly closed, clinical deployment not established |
| LLaMA/Llama 2/3 derivatives | ChatDoctor, MedAlpaca, Clinical Camel, MEDITRON, Med42, XrayGPT | Open ecosystem, local deployment possible | Safety and data provenance vary widely |
| ChatGLM derivatives | DoctorGLM, BianQue | Chinese medical dialogue focus | Narrow language/domain coverage |
| Mistral derivatives | BioMistral | Efficient open medical model, multilingual evaluation | Primarily QA-focused |
| VLM adapters | LLaVA-Med, XrayGPT, CheXagent, MAIRA-2 | Image-grounded conversation/reporting | Visual hallucination and grounding remain difficult |
| Agentic/multi-agent prompting | DERA, MIRAGE graph RAG | Interpretable deliberation and verification | More latency and complexity |

### Table 3. Paper vs Dataset

| Dataset or benchmark | Used or introduced by | Notes |
|---|---|---|
| MedQA | Med-PaLM, GPT-4 challenge, MEDITRON, Clinical Camel, BioMistral | USMLE-style exam QA |
| MedMCQA | Med-PaLM, BioMistral, open medical LLMs | Indian medical entrance exam QA |
| PubMedQA | Med-PaLM, Clinical Camel, BioMistral | Biomedical research QA |
| MMLU clinical topics | Med-PaLM, GPT-4 challenge | Broad knowledge benchmark with clinical subsets |
| HealthSearchQA and MultiMedQA | Med-PaLM | Consumer searched health questions plus six existing QA sets |
| DDXPlus | MedRAG | Differential-diagnosis benchmark |
| CPDD | MedRAG | Private chronic-pain diagnostic dataset |
| BianQueCorpus | BianQue | Multi-turn Chinese health conversations polished by ChatGPT |
| Psych8k and Counseling Bench | ChatCounselor | Real counseling interviews and mental-health support evaluation |
| MultiMedBench | Med-PaLM M | Multimodal biomedical benchmark |
| CheXinstruct and CheXbench | CheXagent | Chest X-ray instruction and evaluation benchmark |
| MIMIC-CXR, CheXpert, RadGraph | MAIRA-2, CheXagent, radiology systems | Radiology report generation and factuality |
| PMC figure-caption data | LLaVA-Med, Med-Flamingo | Biomedical image-text pretraining |
| VQA-RAD, PathVQA, SLAKE, PMC-VQA | LLaVA-Med and related VLMs | Biomedical VQA |
| AfriMed-QA | AfriMed-QA | Pan-African multi-specialty medical QA benchmark |

### Table 4. Paper vs Evaluation Metrics

| Evaluation family | Metrics | Papers |
|---|---|---|
| QA correctness | Accuracy, exact match, F1 | Med-PaLM, GPT-4 challenge, MedMCQA, BioMistral, MEDITRON |
| Clinical human evaluation | Consensus, factuality, harm, bias, helpfulness, completeness | Med-PaLM, Med-PaLM 2, AMIE, Med-Flamingo |
| Dialogue quality | History-taking, empathy, communication, management reasoning, OSCE-style ratings | AMIE, HuatuoGPT, BianQue, DISC-MedLLM |
| RAG quality | Retrieval relevance, hallucination, evidence support, diagnosis specificity, misdiagnosis rate | MedRAG, RAG2 |
| Mental-health outcomes | PHQ-9, GAD-7, distress, Hedges g, therapeutic alliance, adverse events | Therabot, Li et al. meta-analysis |
| Radiology/pathology | VQA accuracy, BLEU/ROUGE/METEOR/CIDEr, CheXpert, RadGraph, RadFact, GREEN, radiologist preference/time | LLaVA-Med, XrayGPT, CheXagent, MAIRA-2, PathChat |

### Table 5. RAG and Human Evaluation

| Paper | RAG/KB usage | Human evaluation |
|---|---|---|
| Med-PaLM | No conventional RAG; instruction prompt tuning and MultiMedQA | Clinician and lay evaluation for consensus, harm, bias, helpfulness |
| GPT-4 medical challenge | No RAG; prompted general LLM | Mostly benchmark and qualitative case analysis |
| ChatDoctor | Self-directed retrieval from online/offline medical sources | NR in this pass |
| HuatuoGPT | No primary RAG; doctor data plus ChatGPT-distilled data and RLAIF | Manual and GPT-4 evaluation reported |
| DISC-MedLLM | Knowledge-graph-derived SFT data, not pure runtime RAG | Single-turn and multi-turn consultation evaluation |
| AMIE | Self-play simulation, not classic RAG | Specialist physician and patient-actor evaluation |
| DERA | Multi-agent deliberation, no classic RAG | Human expert preference for summarization/care plan |
| MedRAG | EHR retrieval plus diagnostic knowledge graph | Evaluated on DDXPlus and private chronic-pain data |
| RAG2 | Biomedical multi-corpus RAG with rationale filtering | Automatic benchmark evaluation |
| Med-Flamingo | Pretraining over medical image-text data, not RAG | Physician review of generative medical VQA |
| CheXagent | Model and workflow evaluation, no classic RAG | Radiologist workflow/time-saving study |

## 7. Datasets

The dataset landscape is uneven. Medical QA datasets are abundant and easy to evaluate, but over-represent exam questions. Clinical dialogue datasets are scarcer, often proprietary, de-identified, synthetic, or derived from online consultation forums. RAG datasets increasingly combine public diagnostic corpora with private EHR-like datasets. Multimodal datasets are strong in radiology but weaker for general clinical images, pathology, dermatology, and longitudinal multimodal patient data. Mental-health datasets are ethically sensitive and often not fully open.

Key dataset gaps:

- Few datasets represent real multi-turn doctor-patient dialogue with uncertainty, missing information, and clinical follow-up.
- Most benchmarks are English or Chinese; low-resource language evidence is weak, with AfriMed-QA a notable correction.
- Patient demographics and social determinants are rarely modeled in a way that supports fairness evaluation.
- Benchmarks often test answer accuracy, not safe refusal, triage, escalation, or longitudinal outcomes.
- RAG benchmarks need gold evidence, source conflict annotations, and citation-verification labels.

## 8. Evaluation Metrics

Medical chatbot evaluation should be layered.

1. Knowledge: MCQ accuracy, open-ended answer correctness, exact match/F1.
2. Reasoning: differential diagnosis quality, reasoning validity, management-plan appropriateness, calibration.
3. Safety: harmfulness, hallucination, contraindicated advice, unsafe omission, crisis escalation.
4. Communication: empathy, clarity, reading level, cultural competence, completeness, refusal quality.
5. Grounding: citation correctness, retrieved evidence relevance, claim-level support.
6. Clinical utility: clinician time saved, workflow fit, patient satisfaction, adherence, outcomes.
7. Equity: subgroup performance, demographic bias, language and geography robustness.
8. Multimodal grounding: pathology/radiology finding correctness, localization, RadGraph/RadFact/GREEN, visual hallucination checks.

Automatic metrics are useful for screening but insufficient for deployment claims. Strong papers increasingly combine benchmark scores with clinician review, patient-actor OSCEs, radiologist workflow studies, or randomized trials.

## 9. Current Trends

- Increasing LLM use: the field moved from scripted bots to GPT/PaLM/LLaMA-family assistants after 2023.
- Medical foundation models: Med-PaLM, MEDITRON, BioMistral, Med42, Clinical Camel, PMC-LLaMA and related systems specialize general LLMs for medicine.
- RAG and knowledge grounding: MedRAG and RAG2 reflect a shift toward retrievable evidence and dynamic medical knowledge.
- Multimodal systems: LLaVA-Med, Med-Flamingo, Med-PaLM M, PathChat, CheXagent, MAIRA-2, and XrayGPT extend chatbots beyond text.
- Synthetic data: ChatGPT/GPT-4 distilled data powers many open models, but risks teacher-error propagation.
- Alignment and preference tuning: HuatuoGPT, Med42-v2, and related work move beyond SFT toward reward/preference alignment.
- Clinical evaluation: AMIE, Therabot, CheXagent, Med-PaLM human evaluation, and PathChat push beyond benchmark-only claims.
- Open-source models: open medical LLMs enable privacy-preserving local deployment but need stronger safety evaluation.
- Closed-source models: GPT-4 and Med-PaLM-class systems remain strong benchmarks but limit reproducibility.
- Safety and hallucination: hallucination, overconfidence, fabricated citations, and visual mirages are now central evaluation targets.

## 10. Research Gaps

1. Lack of real-world clinical validation: most systems are not tested prospectively in clinical workflows.
2. Weak multi-turn clinical benchmarks: current QA benchmarks do not test history-taking, uncertainty, and follow-up.
3. Hallucination and overconfidence: models often sound certain when wrong.
4. Inadequate RAG verification: many systems retrieve evidence but do not verify claim-level support.
5. Limited multilingual and low-resource evidence: English and Chinese dominate.
6. Poor personalization with safety: systems rarely adapt safely to comorbidities, medications, local guidelines, or preferences.
7. Limited long-term memory: few systems model longitudinal patient state with privacy and consent controls.
8. Insufficient physician collaboration design: handoff, escalation, audit trails, and liability remain immature.
9. Regulatory uncertainty: evidence packages rarely map to FDA/EU MDR/clinical governance requirements.
10. Privacy and security: EHR/chat logs raise re-identification, leakage, prompt injection, and retrieval poisoning risks.
11. Bias and fairness: few studies test demographic, geographic, language, disability, and socioeconomic robustness.
12. Mental-health safety: crisis handling, dependency, therapeutic boundaries, and escalation need stronger standards.
13. Multimodal grounding: VLMs need better proof that outputs are based on images rather than priors.
14. Benchmark saturation: exam-style datasets can be memorized or overfit and do not represent clinical practice.
15. Dataset provenance: synthetic and online-consultation data often lack quality labels and clinical accountability.

## 11. Future Directions

- Build standardized multi-turn clinical-chat benchmarks with patient simulators, clinician-authored cases, hidden test sets, and outcome-based scoring.
- Require claim-level evidence grounding for RAG systems, with citation correctness and conflict handling.
- Combine RAG with uncertainty estimation, abstention, and escalation-to-human protocols.
- Develop privacy-preserving medical chatbot learning through federated learning, secure enclaves, synthetic data audits, and on-prem deployment.
- Create multilingual and culturally grounded benchmarks, especially for low- and middle-income settings.
- Evaluate chatbots in prospective clinical studies, not only retrospective benchmarks.
- Design clinician-in-the-loop workflows where chatbots draft, summarize, or triage but humans retain accountability.
- Build medical VLM tests for visual grounding failure, missing-image hallucination, localization, and subtle findings.
- Create mental-health-specific safety standards, including crisis detection, escalation, dependency prevention, and adverse-event reporting.
- Report reproducible model cards: data provenance, excluded uses, safety filters, known failure modes, and deployment constraints.

## 12. Conclusion

AI medical chatbots have progressed from narrow scripted agents to generalist, multimodal, and increasingly agentic medical assistants. The technical frontier is not merely larger LLMs. The field is converging on grounded generation, multi-turn diagnostic dialogue, multimodal reasoning, clinical human evaluation, and safety-oriented deployment. The main scientific gap is the mismatch between benchmark capability and clinical reliability. Future work should prioritize evidence-grounded, auditable, privacy-preserving, clinically validated systems over benchmark-only performance claims.

## Appendix A. Structured Per-Paper Evidence Matrix

Fields compressed per row: title, authors, year, venue, DOI/source, publisher, citation count if confirmed, GitHub/project, medical domain, problem, chatbot category, modalities, model/backbone, fine-tuning/prompting/RAG/KB, datasets, metrics/human evaluation, strengths, weaknesses/limitations, contributions, author-proposed or inferred future work, novel ideas.

| ID | Structured summary |
|---|---|
| P01 | **Large Language Models Encode Clinical Knowledge**. Singhal et al.; 2023; Nature; DOI `10.1038/s41586-023-06291-2`; publisher Springer Nature; citations confirmed on Nature page: 3764 at access time. GitHub/project: NR. Domain: general medical QA. Problem: clinical knowledge and consumer medical questions. Category: LLM medical QA. Modalities: text-to-text. Models: PaLM, Flan-PaLM, Med-PaLM. FT/prompt: instruction prompt tuning, few-shot, CoT, self-consistency. RAG/KB: no runtime RAG. Datasets: MultiMedQA, MedQA, MedMCQA, PubMedQA, MMLU clinical, LiveQA, MedicationQA, HealthSearchQA. Metrics: accuracy plus clinician/lay human evaluation for consensus, harm, bias, reasoning, helpfulness. Strength: rigorous human-evaluation framework. Weakness: not a deployed chatbot and still below clinicians on some axes. Contribution/novelty: MultiMedQA and Med-PaLM. Future: stronger safety, equity, clinical validation. Source: https://www.nature.com/articles/s41586-023-06291-2 |
| P02 | **Toward expert-level medical question answering with large language models**. Singhal et al.; 2025; Nature Medicine; DOI `10.1038/s41591-024-03423-7`; publisher Springer Nature; citations: NR. Project: NR. Domain: medical QA. Category: advanced LLM medical QA. Modalities: text. Models: Med-PaLM 2/PaLM-family. FT/prompt: improved alignment and prompting over Med-PaLM. RAG: NR. Datasets: MultiMedQA-style medical QA. Metrics: expert-level QA accuracy and human evaluation. Strength: raises benchmark ceiling. Weakness: closed system, limited deployment evidence. Novelty: expert-level medical QA framing. Source: https://www.nature.com/articles/s41591-024-03423-7 |
| P03 | **Towards Conversational Diagnostic AI**. Tu et al.; 2024; arXiv; DOI N/A; citations: NR. Project: NR. Domain: primary-care diagnostic dialogue. Category: diagnostic consultation chatbot. Modalities: text chat. Model: AMIE, LLM-based. FT/prompt: self-play simulated consultations and automated feedback. RAG: not conventional. Datasets: 149 OSCE-style cases from Canada, UK, India. Metrics: specialist-physician and patient-actor ratings, diagnosis accuracy, history-taking, management, empathy. Strength: evaluates multi-turn diagnosis rather than static QA. Weakness: actor text-chat differs from real clinical practice. Novelty: self-play diagnostic dialogue training. Future: real clinical validation. Source: https://arxiv.org/abs/2401.05654 |
| P04 | **Capabilities of GPT-4 on Medical Challenge Problems**. Nori et al.; 2023; arXiv; DOI N/A. Domain: exams and medical challenge problems. Category: general LLM evaluation as medical assistant. Modalities: text and some image-containing questions. Model: GPT-4. FT: none reported. Prompting: no specialized prompt crafting, with qualitative case analysis. RAG: no. Datasets: USMLE practice materials, MultiMedQA. Metrics: exam accuracy, calibration, qualitative reasoning. Human eval: limited. Strength: showed GPT-4 outperforms many earlier medical-specific baselines. Weakness: benchmark performance is not clinical safety. Source: https://arxiv.org/abs/2303.13375 |
| P05 | **Performance of ChatGPT on USMLE: Potential for AI-assisted medical education using large language models**. Kung et al.; 2023; PLOS Digital Health; DOI `10.1371/journal.pdig.0000198`; publisher PLOS. Domain: medical education. Category: ChatGPT evaluation. Modalities: text. Model: ChatGPT/GPT-3.5 era. FT/RAG: none. Datasets: USMLE-style items. Metrics: pass/fail and explanation quality. Human eval: limited. Strength: early evidence of LLM medical exam competence. Weakness: exam-oriented. Source: https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0000198 |
| P06 | **How Does ChatGPT Perform on the United States Medical Licensing Examination?** Gilson et al.; 2023; JMIR Medical Education; DOI: NR. Domain: medical education. Category: ChatGPT evaluation. Modalities: text. Model: ChatGPT. FT/RAG: none. Datasets: USMLE-style questions. Metrics: correctness and educational implications. Strength: early independent USMLE evaluation. Weakness: not a clinical chatbot deployment. Source pointer: cited in ChatGPT medical bibliography at https://en.wikipedia.org/wiki/ChatGPT |
| P07 | **Comparing Physician and Artificial Intelligence Chatbot Responses to Patient Questions Posted to a Public Social Media Forum**. Ayers et al.; 2023; JAMA Internal Medicine; DOI: NR in this pass. Domain: patient questions. Category: patient QA chatbot evaluation. Modalities: text. Model: ChatGPT. FT/RAG: none. Datasets: Reddit AskDocs questions and physician replies. Metrics: blinded ratings of quality and empathy. Strength: evaluates real patient questions and communication. Weakness: online forum context, not established physician-patient relationship; factual accuracy not the only outcome. Source pointer: https://en.wikipedia.org/wiki/Artificial_intelligence_in_healthcare |
| P08 | **ChatDoctor: A Medical Chat Model Fine-Tuned on LLaMA Using Medical Domain Knowledge**. Li et al.; 2023; arXiv. Domain: patient-doctor consultation. Category: domain-fine-tuned medical chatbot plus retrieval. Modalities: text. Backbone: LLaMA. FT: 100k patient-doctor dialogues. Prompting: medical dialogue. RAG: self-directed retrieval from online/offline sources. Datasets: online consultation dialogues. Metrics: NR in this matrix. Strength: early open medical chat model with retrieval. Weakness: online consultation data quality and safety. GitHub: NR in source snippet. Source: https://arxiv.org/abs/2303.14070 |
| P09 | **MedAlpaca: An Open-Source Collection of Medical Conversational AI Models and Training Data**. Han et al.; 2023; arXiv. Domain: general medical conversation and exams. Category: open medical instruction tuning. Modalities: text. Backbone: Alpaca/LLaMA-family. FT: 160k+ medical instruction entries. RAG: no. Datasets: curated medical instructions and exams. Metrics: medical certification exams. Strength: reproducible open data/model direction. Weakness: benchmark-heavy evaluation. Source: https://arxiv.org/abs/2304.08247 |
| P10 | **PMC-LLaMA: Towards Building Open-source Language Models for Medicine**. Wu et al.; 2023; arXiv. Domain: medical QA and dialogue. Category: open medical LLM. Modalities: text. Backbone: LLaMA. FT: continued pretraining on 4.8M biomedical papers and 30k textbooks, instruction tuning on QA/rationale/dialogue. RAG: no runtime RAG. Datasets: medical QA and instruction data, 202M tokens. Metrics: public QA benchmarks. Strength: strong domain knowledge injection. Weakness: pretraining does not guarantee safe dialogue. GitHub: https://github.com/chaoyi-wu/PMC-LLaMA. Source: https://arxiv.org/abs/2304.14454 |
| P11 | **ClinicalGPT: Large Language Models Finetuned with Diverse Medical Data and Comprehensive Evaluation**. Wang et al.; 2023; arXiv. Domain: clinical scenarios. Category: medical LLM. Modalities: text. Backbone: NR. FT: medical records, domain knowledge, multi-round consultation data. RAG: no. Datasets: diverse real-world medical data. Metrics: medical QA, exams, consultations, diagnostic medical-record analysis. Strength: broad evaluation framing. Weakness: data provenance and deployment evidence need scrutiny. Source: https://arxiv.org/abs/2306.09968 |
| P12 | **DoctorGLM: Fine-tuning your Chinese Doctor is not a Herculean Task**. Xiong et al.; 2023; arXiv. Domain: Chinese medical dialogue. Category: Chinese medical chatbot. Modalities: text. Backbone: ChatGLM-6B. FT: Chinese medical dialogues collected with ChatGPT assistance. RAG: NR. Metrics: NR. Strength: low-cost fine-tuning recipe. Weakness: authors state early-stage system contains mistakes. GitHub: https://github.com/xionghonglin/DoctorGLM. Source: https://arxiv.org/abs/2304.01097 |
| P13 | **HuatuoGPT, towards Taming Language Model to Be a Doctor**. Zhang et al.; 2023; arXiv. Domain: medical consultation. Category: aligned medical chatbot. Modalities: text. Backbone: LLM, specific base varies by release. FT: ChatGPT-distilled data plus real doctor data. Prompting: consultation. RAG: no primary runtime RAG. KB: doctor data. Metrics: automatic, GPT-4, and human evaluation; medical benchmarks. Strength: combines synthetic and real doctor data. Weakness: teacher-model and doctor-data biases. GitHub/project: https://github.com/FreedomIntelligence/HuatuoGPT and https://www.HuatuoGPT.cn/. Source: https://arxiv.org/abs/2305.15075 |
| P14 | **BianQue: Balancing the Questioning and Suggestion Ability of Health LLMs with Multi-turn Health Conversations Polished by ChatGPT**. Chen et al.; 2023; arXiv. Domain: proactive health consultation. Category: multi-turn health chatbot. Modalities: text. Backbone: ChatGLM. FT: BianQueCorpus. Prompting: chain of questioning. RAG: no. Metrics: questioning and suggestion ability. Strength: targets missing follow-up-question behavior. Weakness: synthetic polishing may bias dialogue. Source: https://arxiv.org/abs/2310.15896 |
| P15 | **HuatuoGPT-II, One-stage Training for Medical Adaption of LLMs**. Chen et al.; 2023; arXiv. Domain: Chinese medicine and medical exams. Category: medical LLM adaptation. Modalities: text. Backbone: Llama2-family. FT: unified input-output transformation across heterogeneous pretraining/SFT data. RAG: no. Datasets: Chinese medicine and licensing exams. Metrics: benchmark and expert manual evaluation. Strength: simplifies domain-adaptation pipeline. Weakness: strong Chinese/TCM focus. Source: https://arxiv.org/abs/2311.09774 |
| P16 | **DISC-MedLLM: Bridging General Large Language Models and Real-World Medical Consultation**. Bao et al.; 2023; arXiv. Domain: real-world medical consultation. Category: medical consultation chatbot. Modalities: text. Backbone: general LLM. FT: KG-derived data, reconstructed dialogues, human-guided preference rephrasing. RAG: not runtime RAG; KG used for training data. Datasets: SFT data released. Metrics: single-turn and multi-turn consultation evaluation. Strength: aligns toward real consultation. Weakness: external clinical validation lacking. GitHub: https://github.com/FudanDISC/DISC-MedLLM. Source: https://arxiv.org/abs/2308.14346 |
| P17 | **Clinical Camel: An Open Expert-Level Medical Language Model with Dialogue-Based Knowledge Encoding**. Toma et al.; 2023; arXiv. Domain: clinical research and QA. Category: open medical LLM. Modalities: text. Backbone: LLaMA-2. FT: QLoRA and dialogue-based knowledge encoding. RAG: no. Datasets: USMLE, PubMedQA, MedQA, MedMCQA. Metrics: benchmark accuracy. Strength: efficient open fine-tuning. Weakness: authors stress need for rigorous human safety evaluation. Source: https://arxiv.org/abs/2305.12031 |
| P18 | **MEDITRON-70B: Scaling Medical Pretraining for Large Language Models**. Chen et al.; 2023; arXiv. Domain: medical knowledge and QA. Category: medical foundation LLM. Modalities: text. Backbone: Llama-2 7B/70B. FT: continued pretraining on PubMed, abstracts, guidelines; task fine-tuning. RAG: no. Datasets: four major medical benchmarks. Metrics: benchmark accuracy. Strength: large open medical pretraining. Weakness: QA evidence does not equal clinical deployment. Source: https://arxiv.org/abs/2311.16079 |
| P19 | **BioMistral: A Collection of Open-Source Pretrained Large Language Models for Medical Domains**. Labrak et al.; 2024; arXiv. Domain: biomedical/medical QA. Category: open medical LLM. Modalities: text. Backbone: Mistral. FT: continued pretraining on PubMed Central, quantization/model merging. RAG: no. Datasets: 10 medical QA tasks; multilingual translated benchmark. Metrics: QA accuracy. Strength: multilingual evaluation. Weakness: mostly benchmark QA. Source: https://arxiv.org/abs/2402.10373 |
| P20 | **Med42-v2: A Suite of Clinical LLMs**. Christophe et al.; 2024; arXiv. Domain: clinical prompts and QA. Category: clinical LLM suite. Modalities: text. Backbone: Llama 3. FT: specialized clinical data, multi-stage preference alignment. RAG: no. Datasets: medical benchmarks. Metrics: benchmark comparison to Llama3 and GPT-4. Strength: open clinical alignment. Weakness: benchmark-heavy. Project: https://huggingface.co/m42-health. Source: https://arxiv.org/abs/2408.06142 |
| P21 | **SM70: A Large Language Model for Medical Devices**. Bhatti et al.; 2023; arXiv. Domain: medical-device healthcare QA. Category: domain LLM. Modalities: text. Backbone: Llama2 70B. FT: QLoRA on MedAlpaca entries. RAG: no. Datasets: MedQA-USMLE, PubMedQA, USMLE. Metrics: benchmark accuracy. Strength: targeted large model. Weakness: narrow provenance and not peer-reviewed. Source: https://arxiv.org/abs/2312.06974 |
| P22 | **DERA: Enhancing Large Language Model Completions with Dialog-Enabled Resolving Agents**. Nair et al.; 2023; arXiv. Domain: medical summarization, care planning, QA. Category: multi-agent clinical assistant. Modalities: text. Backbone: GPT-4. FT: no. Prompting: researcher-decider dialogue. RAG: no classic RAG. Datasets: clinical conversation summarization, care-plan generation, open-ended MedQA. Metrics: human expert preference and quantitative metrics. Strength: interpretable multi-agent refinement. Weakness: closed LLM and added latency. GitHub: https://github.com/curai/curai-research/tree/main/DERA. Source: https://arxiv.org/abs/2303.17071 |
| P23 | **MedMCQA: A Large-scale Multi-Subject Multi-Choice Dataset for Medical domain Question Answering**. Pal et al.; 2022; arXiv. Domain: medical exams. Category: benchmark paper. Modalities: text. Model: N/A. Datasets: 194k AIIMS/NEET PG questions, 21 subjects. Metrics: MCQ accuracy. Strength: large scale and subject diversity. Weakness: exam benchmark, not dialogue. Source: https://arxiv.org/abs/2203.14371 |
| P24 | **AfriMed-QA: A Pan-African, Multi-Specialty, Medical Question-Answering Benchmark Dataset**. Olatunji et al.; 2024; arXiv. Domain: African medical education and specialties. Category: benchmark and equity evaluation. Modalities: text. Models: 30 LLMs. Datasets: 15k questions from over 60 medical schools, 16 countries, 32 specialties. Metrics: correctness and demographic bias; human preference. Strength: addresses geographic benchmark gap. Weakness: QA benchmark, not deployed chat. Source: https://arxiv.org/abs/2411.15640 |
| P25 | **MedRAG: Enhancing Retrieval-augmented Generation with Knowledge Graph-Elicited Reasoning for Healthcare Copilot**. Zhao et al.; 2025; arXiv. Domain: diagnosis and chronic pain. Category: RAG healthcare copilot. Modalities: text/EHR-like. Backbone: LLM with RAG. FT: NR. Prompting: KG-elicited reasoning. RAG: EHR retrieval plus four-tier diagnostic KG. Datasets: DDXPlus, private CPDD. Metrics: diagnosis specificity, misdiagnosis reduction. Strength: structured KG improves similar-disease differentiation. Weakness: private data limits reproducibility. GitHub planned: https://github.com/SNOWTEAM2023/MedRAG. Source: https://arxiv.org/abs/2502.04413 |
| P26 | **Rationale-Guided Retrieval Augmented Generation for Medical Question Answering**. Sohn et al.; 2024; arXiv. Domain: biomedical QA. Category: RAG medical QA. Modalities: text. Backbone: multiple LLMs. FT: small filtering model. Prompting: LLM-generated rationales as retrieval queries. RAG: multi-corpus biomedical retrieval and evidence filtering. Datasets: three medical QA benchmarks. Metrics: benchmark accuracy improvements. Strength: tackles noisy retrieval and retriever bias. Weakness: QA-focused. GitHub: https://github.com/dmis-lab/RAG2. Source: https://arxiv.org/abs/2411.00300 |
| P27 | **MIRAGE: Scaling Test-Time Inference with Parallel Graph-Retrieval-Augmented Reasoning Chains**. Wei et al.; 2025; arXiv. Domain: medical QA. Category: graph-RAG reasoning chatbot component. Modalities: text. Backbone: reasoning LLMs. Prompting: decomposed subquestions and parallel chains. RAG: medical KG graph exploration. Datasets: GenMedGPT-5k, CMCQA, ExplainCPE. Metrics: automatic and human evaluation. Strength: traceable multi-chain reasoning. Weakness: preprint, computational complexity. Source: https://arxiv.org/abs/2508.18260 |
| P28 | **MIRAGE: Retrieval and Generation of Multimodal Images and Texts for Medical Education**. Diaz Benito et al.; 2026; arXiv. Domain: medical education. Category: multimodal retrieval/generation assistant. Modalities: text and images to images/text. Models: medical CLIP, medical diffusion, Dolly-v2-3b. FT: MedICaT-ROCO/ROCO-style. RAG: multimodal retrieval. Metrics: NR. Strength: educational interactive retrieval/generation. Weakness: not clinical decision support. Project: deployed on Kaggle per paper. Source: https://arxiv.org/abs/2605.04772 |
| P29 | **LLaVA-Med: Training a Large Language-and-Vision Assistant for Biomedicine in One Day**. Li et al.; 2023; arXiv. Domain: biomedical image conversation. Category: vision-language medical chatbot. Modalities: image+text to text. Backbone: LLaVA/Vicuna-style VLM. FT: PMC image-caption alignment and GPT-4-generated instruction data. RAG: no. Datasets: PMC figures, biomedical VQA datasets. Metrics: VQA metrics. Strength: fast biomedical VLM adaptation. Weakness: biomedical figures differ from clinical images. Source: https://arxiv.org/abs/2306.00890 |
| P30 | **Med-Flamingo: a Multimodal Medical Few-shot Learner**. Moor et al.; 2023; arXiv. Domain: medical VQA. Category: multimodal medical assistant. Modalities: image+text to text. Backbone: OpenFlamingo-9B. FT: continued pretraining on paired/interleaved medical image-text data. RAG: no. Datasets: medical VQA and visual USMLE-style data. Metrics: clinician ratings and VQA performance. Strength: few-shot multimodal ability and physician evaluation. Weakness: few-shot setting still not deployment. GitHub: https://github.com/snap-stanford/med-flamingo. Source: https://arxiv.org/abs/2307.15189 |
| P31 | **XrayGPT: Chest Radiographs Summarization using Medical Vision-Language Models**. Thawkar et al.; 2023; arXiv. Domain: chest radiology. Category: radiology VLM chatbot. Modalities: X-ray+text to text. Backbone: MedCLIP plus Vicuna. FT: alignment and 217k generated interactive summaries from radiology reports. RAG: no. Datasets: chest radiograph report-derived instruction data. Metrics: report/VQA-style evaluation. Strength: radiology-specific visual conversation. Weakness: generated summaries may encode errors. GitHub: https://github.com/mbzuai-oryx/XrayGPT. Source: https://arxiv.org/abs/2306.07971 |
| P32 | **Towards Generalist Biomedical AI**. Tu et al.; 2023; arXiv. Domain: multimodal biomedicine. Category: generalist multimodal medical assistant. Modalities: text, imaging, genomics, other biomedical data. Model: Med-PaLM M. FT: multimodal training. RAG: no. Datasets: MultiMedBench. Metrics: task-specific benchmark metrics and radiologist report preference. Strength: broad multimodal scope. Weakness: proof-of-concept, not deployment. Source: https://arxiv.org/abs/2307.14334 |
| P33 | **A multimodal generative AI copilot for human pathology**. Lu et al.; 2024; Nature; DOI `10.1038/s41586-024-07618-3`; publisher Springer Nature. Domain: pathology. Category: pathology copilot chatbot. Modalities: pathology image+text to text. Backbone: PathChat system. FT: pathology-specific multimodal training. RAG: NR. Datasets/metrics: pathology VQA and expert evaluation. Strength: real specialty copilot direction. Weakness: deployment and regulatory validation still needed. Source: https://www.nature.com/articles/s41586-024-07618-3 |
| P34 | **A Vision-Language Foundation Model to Enhance Efficiency of Chest X-ray Interpretation**. Chen et al.; 2024; arXiv. Domain: chest radiology workflow. Category: radiology assistant. Modalities: CXR+text to text/tasks. Model: CheXagent. FT: CheXinstruct. RAG: no. Datasets: CheXinstruct, CheXbench. Metrics: eight task types plus radiologist workflow time/quality. Strength: workflow utility measured, not only benchmark. Weakness: chest-X-ray-specific. Source: https://arxiv.org/abs/2401.12208 |
| P35 | **MAIRA-2: Grounded Radiology Report Generation**. Bannur et al.; 2024; arXiv. Domain: radiology reporting. Category: grounded multimodal report assistant. Modalities: CXR+context to report and localization. Model: MAIRA-2. FT: radiology-specific multimodal training. RAG: no. Datasets: CXR report-generation benchmarks. Metrics: RadFact, correctness, completeness, grounding. Strength: grounded report generation. Weakness: radiology-only. Source: https://arxiv.org/abs/2406.04449 |
| P36 | **BioMedGPT: Open Multimodal Generative Pre-trained Transformer for BioMedicine**. Luo et al.; 2023; arXiv. Domain: biomedical QA, molecules, proteins. Category: multimodal biomedical assistant. Modalities: text, molecules, proteins. Backbone: BioMedGPT-LM/Llama2-derived. FT: modality alignment and biomedical pretraining. RAG: no. Datasets: PubChemQA, UniProtQA, biomedical QA. Metrics: QA task performance. Strength: bridges biological modalities and language. Weakness: less clinical/patient-facing. GitHub: https://github.com/PharMolix/OpenBioMed. Source: https://arxiv.org/abs/2308.09442 |
| P37 | **MedBLIP: Bootstrapping Language-Image Pre-training from 3D Medical Images and Texts**. Chen et al.; 2023; arXiv. Domain: Alzheimer's disease imaging. Category: medical VLP assistant component. Modalities: 3D image+text. Backbone: frozen image encoders plus frozen LLM, MedQFormer. FT: bridge module. RAG: no. Datasets: ADNI, NACC, OASIS, AIBL, MIRIAD. Metrics: zero-shot classification and medical VQA. Strength: 3D medical-image VLP. Weakness: narrow AD domain. GitHub: https://github.com/Qybc/MedBLIP. Source: https://arxiv.org/abs/2305.10799 |
| P38 | **CheXmix: Unified Generative Pretraining for Vision Language Models in Medical Imaging**. Kumar et al.; 2026; arXiv. Domain: chest X-ray. Category: generative VLM assistant. Modalities: CXR+text. Model: early-fusion generative model. FT: unified multimodal pretraining. RAG: no. Datasets: chest X-ray/report corpus. Metrics: AUROC, GREEN, inpainting/report metrics. Strength: critiques projection bottleneck and improves fine-grained capture. Weakness: preprint. GitHub: https://github.com/StanfordMIMI/CheXmix. Source: https://arxiv.org/abs/2604.22989 |
| P39 | **Systematic review and meta-analysis of AI-based conversational agents for promoting mental health and well-being**. Li et al.; 2023; npj Digital Medicine; DOI `10.1038/s41746-023-00979-5`; publisher Springer Nature; citations confirmed: 528 at access time. Domain: mental health. Category: evidence synthesis for conversational agents. Modalities: mostly text/mobile, some multimodal. Models: retrieval, generative, NLP/ML. Datasets: 35 eligible studies, 15 RCTs in meta-analysis. Metrics: Hedges g for depression, distress, well-being; user experience. Strength: strongest synthesis of intervention evidence. Weakness: heterogeneity and many small studies. Source: https://www.nature.com/articles/s41746-023-00979-5 |
| P40 | **SoulChat: Improving LLMs' Empathy, Listening, and Comfort Abilities through Fine-tuning with Multi-turn Empathy Conversations**. Chen et al.; 2023; arXiv. Domain: mental health support. Category: empathetic counseling chatbot. Modalities: text. Backbone: LLM. FT: over 2M multi-turn empathetic conversation samples. RAG: no. Metrics: empathy/listening/support evaluation. Strength: targets empathy rather than only advice. Weakness: empathy does not equal clinical safety. Source: https://arxiv.org/abs/2311.00273 |
| P41 | **ChatCounselor: A Large Language Models for Mental Health Support**. Liu et al.; 2023; arXiv. Domain: mental health counseling. Category: mental-health chatbot. Modalities: text. Backbone: LLM. FT: Psych8k from 260 in-depth psychologist-client interviews. Prompting: counseling evaluation prompts. RAG: no. Datasets: Psych8k, Counseling Bench. Metrics: GPT-4 rubric across seven counseling metrics. Strength: high-quality domain data. Weakness: small interview set and LLM-as-judge concerns. Source: https://arxiv.org/abs/2309.15461 |
| P42 | **Mental-LLM: Leveraging Large Language Models for Mental Health Prediction via Online Text Data**. Xu et al.; 2023; arXiv. Domain: mental health prediction. Category: mental-health LLM component, not therapy chatbot. Modalities: text. Models: Alpaca, FLAN-T5, GPT-3.5, GPT-4, fine-tuned Mental-Alpaca and Mental-FLAN-T5. FT: instruction fine-tuning. RAG: no. Datasets: online mental-health prediction tasks. Metrics: balanced accuracy. Strength: broad LLM comparison. Weakness: prediction is not counseling; bias concerns. Source: https://arxiv.org/abs/2307.14385 |
| P43 | **Randomized Trial of a Generative AI Chatbot for Mental Health Treatment**. Heinz et al.; 2025; NEJM AI; DOI `10.1056/AIoa2400802`. Domain: mental health treatment. Category: generative therapy chatbot. Modalities: text. Model: Therabot. FT/prompt/RAG: NR in this pass. Datasets: clinical trial participants. Metrics: symptom outcomes and trial endpoints. Strength: randomized-trial evidence. Weakness: long-term safety and generalizability need more evidence. Source pointer: https://ai.nejm.org/doi/full/10.1056/AIoa2400802 |
| P44 | **Rethinking Large Language Models in Mental Health Applications**. Ji et al.; 2023; arXiv. Domain: mental health safety. Category: critical evaluation/framework. Modalities: text. Models: LLMs. FT/RAG: N/A. Metrics: ethics/safety analysis; discussion of hallucination, instability, interpretability, and counselor irreplaceability. Strength: highlights mental-health-specific risks. Weakness: not a system paper. Source: https://arxiv.org/abs/2311.11267 |
| P45 | **Risks from Language Models for Automated Mental Healthcare: Ethics and Structure for Implementation**. Grabb et al.; 2024; arXiv. Domain: automated mental health care. Category: safety and implementation framework. Modalities: text. Models: 14 LLMs, including off-the-shelf and fine-tuned models. FT/RAG: N/A. Datasets: 16 clinician-designed mental-health questionnaires. Metrics: clinician-evaluated responses to psychosis, mania, depression, suicidal thoughts, homicidal tendencies, and safety behaviors. Strength: clinician-designed risk assessment and autonomy framework. Weakness: preprint and scenario-based evaluation. Source: https://arxiv.org/abs/2406.11852 |
| P46 | **Evaluating the Clinical Safety of LLMs in Response to High-Risk Mental Health Disclosures**. Shah et al.; 2025; arXiv. Domain: crisis-level mental-health disclosures. Category: safety evaluation for chatbot responses. Modalities: text. Models: Claude, Gemini, DeepSeek, ChatGPT, Grok 3, LLaMA. FT/RAG: N/A. Metrics: clinician-coded risk acknowledgment, empathy, help-seeking encouragement, resources, invitation to continue. Strength: directly tests crisis-response behavior. Weakness: preprint and simulated prompts. Source: https://arxiv.org/abs/2509.08839 |
| P47 | **PediatricsGPT: Large Language Models as Chinese Medical Assistants for Pediatric Applications**. Yang et al.; 2024; arXiv. Domain: Chinese pediatrics. Category: specialty medical assistant. Modalities: text. Backbone: LLM. FT: PedCorpus with over 300k multi-task instructions, continuous pretraining, SFT, preference optimization, expert routing. RAG/KB: pediatric textbooks, guidelines, and knowledge-graph resources used in data construction. Metrics: automatic metrics, GPT-4, and doctor evaluations. Strength: specialty-specific pediatric instruction corpus and evaluation. Weakness: Chinese pediatric focus, preprint. Source: https://arxiv.org/abs/2405.19266 |
| P48 | **Can Large Language Models Function as Qualified Pediatricians? A Systematic Evaluation in Real-World Clinical Contexts**. Zhu et al.; 2025; arXiv. Domain: pediatrics. Category: benchmark/evaluation for pediatric chat assistants. Modalities: text. Models: 12 LLMs including GPT-4o, Qwen3, DeepSeek-V3. FT/RAG: N/A. Datasets: PEDIASBench, 19 pediatric subspecialties and 211 prototypical diseases. Metrics: basic knowledge, dynamic diagnosis/treatment, safety, ethics, humanistic sensitivity. Strength: dynamic pediatric clinical reasoning focus. Weakness: benchmark study, not deployment. Source: https://arxiv.org/abs/2511.13381 |
| P49 | **Evaluating Large Language Models for Evidence-Based Clinical Question Answering**. Wang and Chen; 2025; arXiv. Domain: evidence-based clinical QA. Category: RAG/evidence QA evaluation. Modalities: text. Models: GPT-4o-mini, GPT-5. FT: none. Prompting: evidence-based QA and retrieval-augmented prompting. RAG: gold-source abstract, top PubMed abstracts, random abstracts. Datasets: Cochrane systematic reviews, clinical guidelines, AHA recommendations, insurer narrative guidance. Metrics: accuracy by source type, impact of retrieval quality. Strength: shows targeted retrieval improves previously wrong answers. Weakness: preprint and QA rather than open clinical chat. Source: https://arxiv.org/abs/2509.10843 |
| P50 | **Evaluating Large Language Models on Rare Disease Diagnosis: A Case Study using House M.D.** Gupta et al.; 2025; arXiv. Domain: rare-disease diagnosis education. Category: diagnostic reasoning benchmark. Modalities: text. Models: GPT-4o mini, GPT-5 mini, Gemini 2.5 Flash, Gemini 2.5 Pro. FT/RAG: N/A. Datasets: 176 symptom-diagnosis pairs extracted from House M.D. and validated as an educational rare-disease benchmark. Metrics: diagnostic accuracy. Strength: probes rare-disease narrative reasoning. Weakness: television-derived benchmark limits clinical realism. Source: https://arxiv.org/abs/2511.10912 |
| P51 | **Limitations of Large Language Models in Clinical Problem-Solving Arising from Inflexible Reasoning**. Kim et al.; 2025; arXiv. Domain: clinical reasoning. Category: limitation benchmark. Modalities: text. Models: o1, Gemini and other LLMs. FT/RAG: N/A. Datasets: M-ARC. Metrics: clinical abstraction/reasoning accuracy and uncertainty. Strength: exposes benchmark-saturated reasoning failures. Weakness: not a chatbot system. Source: https://arxiv.org/abs/2502.04381 |
| P52 | **BioGPT: Generative Pre-trained Transformer for Biomedical Text Generation and Mining**. Luo et al.; 2022; Briefings in Bioinformatics, source not fully verified in this pass. Domain: biomedical text generation/mining. Category: biomedical generative model background. Modalities: text. Backbone: GPT-style. FT: biomedical literature pretraining. RAG: no. Datasets/metrics: biomedical NLP benchmarks. Strength: influential biomedical generative precursor. Weakness: not a chatbot. Source: cited within Med-PaLM Nature page as BioGPT baseline. |

## Appendix B. Source Links Used in This Pass

- Med-PaLM: https://www.nature.com/articles/s41586-023-06291-2
- Med-PaLM 2: https://www.nature.com/articles/s41591-024-03423-7
- AMIE: https://arxiv.org/abs/2401.05654
- GPT-4 medical challenge: https://arxiv.org/abs/2303.13375
- ChatDoctor: https://arxiv.org/abs/2303.14070
- MedAlpaca: https://arxiv.org/abs/2304.08247
- PMC-LLaMA: https://arxiv.org/abs/2304.14454
- ClinicalGPT: https://arxiv.org/abs/2306.09968
- DoctorGLM: https://arxiv.org/abs/2304.01097
- HuatuoGPT: https://arxiv.org/abs/2305.15075
- BianQue: https://arxiv.org/abs/2310.15896
- HuatuoGPT-II: https://arxiv.org/abs/2311.09774
- DISC-MedLLM: https://arxiv.org/abs/2308.14346
- Clinical Camel: https://arxiv.org/abs/2305.12031
- MEDITRON-70B: https://arxiv.org/abs/2311.16079
- BioMistral: https://arxiv.org/abs/2402.10373
- Med42-v2: https://arxiv.org/abs/2408.06142
- DERA: https://arxiv.org/abs/2303.17071
- MedMCQA: https://arxiv.org/abs/2203.14371
- AfriMed-QA: https://arxiv.org/abs/2411.15640
- MedRAG: https://arxiv.org/abs/2502.04413
- RAG2: https://arxiv.org/abs/2411.00300
- LLaVA-Med: https://arxiv.org/abs/2306.00890
- Med-Flamingo: https://arxiv.org/abs/2307.15189
- XrayGPT: https://arxiv.org/abs/2306.07971
- Med-PaLM M: https://arxiv.org/abs/2307.14334
- PathChat: https://www.nature.com/articles/s41586-024-07618-3
- CheXagent: https://arxiv.org/abs/2401.12208
- MAIRA-2: https://arxiv.org/abs/2406.04449
- BioMedGPT: https://arxiv.org/abs/2308.09442
- MedBLIP: https://arxiv.org/abs/2305.10799
- CheXmix: https://arxiv.org/abs/2604.22989
- Mental-health CA meta-analysis: https://www.nature.com/articles/s41746-023-00979-5
- SoulChat: https://arxiv.org/abs/2311.00273
- ChatCounselor: https://arxiv.org/abs/2309.15461
- Mental-LLM: https://arxiv.org/abs/2307.14385
- Therabot: https://ai.nejm.org/doi/full/10.1056/AIoa2400802
- Rethinking LLMs in mental health: https://arxiv.org/abs/2311.11267
- Risks from language models for automated mental healthcare: https://arxiv.org/abs/2406.11852
- Clinical safety of LLMs for high-risk mental-health disclosures: https://arxiv.org/abs/2509.08839
- PediatricsGPT: https://arxiv.org/abs/2405.19266
- Pediatric LLM real-world clinical contexts: https://arxiv.org/abs/2511.13381
- Evidence-based clinical QA: https://arxiv.org/abs/2509.10843
- Rare-disease diagnosis with House M.D.: https://arxiv.org/abs/2511.10912
