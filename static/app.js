const transcriptEl = document.querySelector("#transcript");
const messageForm = document.querySelector("#messageForm");
const messageInput = document.querySelector("#messageInput");
const startButton = document.querySelector("#startButton");
const voiceButton = document.querySelector("#voiceButton");
const sendButton = document.querySelector("#sendButton");
const saveReportButton = document.querySelector("#saveReportButton");
const reportOutput = document.querySelector("#reportOutput");
const stepValue = document.querySelector("#stepValue");
const painValue = document.querySelector("#painValue");
const redFlagValue = document.querySelector("#redFlagValue");
const identityValue = document.querySelector("#identityValue");
const statusText = document.querySelector("#statusText");
const statusDot = document.querySelector("#statusDot");
const languageSelect = document.querySelector("#languageSelect");
const eyebrowText = document.querySelector("#eyebrowText");
const appTitle = document.querySelector("#appTitle");
const disclaimerText = document.querySelector("#disclaimerText");
const languageLabel = document.querySelector("#languageLabel");
const stateTitle = document.querySelector("#stateTitle");
const stepLabel = document.querySelector("#stepLabel");
const painLabel = document.querySelector("#painLabel");
const redFlagLabel = document.querySelector("#redFlagLabel");
const identityLabel = document.querySelector("#identityLabel");
const reportTitle = document.querySelector("#reportTitle");

let sessionId = null;
let lastState = null;
let recognition = null;
let recognizing = false;
let autoVoiceEnabled = true;
let assistantSpeaking = false;
let selectedVoice = null;
let currentLanguage = "zh-CN";
let activeAudio = null;

const UI = {
  "zh-CN": {
    htmlLang: "zh-CN",
    eyebrow: "本地原型",
    title: "骨关节炎疼痛随访",
    disclaimer: "研究原型：尚未批准用于临床。",
    language: "语言",
    ready: "准备就绪",
    starting: "正在开始",
    listening: "正在听",
    processing: "处理中",
    speaking: "正在说话",
    complete: "已完成",
    urgentFlag: "紧急标记",
    error: "错误",
    voiceUnavailable: "语音不可用",
    start: "开始随访",
    restart: "重新开始",
    mic: "语音",
    micStartLabel: "开始语音输入",
    micStopLabel: "停止语音输入",
    inputPlaceholder: "可以直接说，也可以输入回答",
    inputAria: "回答",
    send: "发送",
    sendAria: "发送回答",
    stateTitle: "随访状态",
    step: "步骤",
    pain: "疼痛",
    redFlags: "危险信号",
    identity: "身份",
    report: "医生报告",
    save: "保存",
    notStarted: "未开始",
    notCaptured: "未记录",
    notScreened: "未筛查",
    notConfirmed: "未确认",
    noUrgentFlags: "没有紧急危险信号",
    uncertain: "不确定",
    yes: "是",
    reportPending: "随访完成后，这里会显示报告。",
    systemIntro: "本地原型支持输入和浏览器语音。准备好后开始随访。",
    voiceUnavailableMessage: "当前浏览器语音输入不可用，您可以继续输入回答。",
    savedPrefix: "报告已保存到 ",
    saveFailed: "无法保存报告。",
    sessionNotStarted: "请先开始随访。",
    stepLabels: {
      readiness_hearing: "听力确认",
      readiness_time: "时间确认",
      permission: "同意继续",
      identity: "身份确认",
      respondent_source: "回答来源",
      average_pain_score: "24小时平均疼痛",
      current_pain_score: "当前疼痛",
      pain_location: "疼痛部位",
      functional_impact: "功能影响",
      usual_comparison: "和平时比较",
      treatment_context: "治疗情况",
      side_effects: "副作用",
      side_effect_description: "症状描述",
      side_effect_start: "开始时间",
      side_effect_status: "症状状态",
      side_effect_severity: "严重程度",
      medication_changed: "用药变化",
      doctor_contacted: "联系医生",
      emergency_visit: "急诊/住院",
      red_flags: "安全筛查",
      complete: "完成",
    },
  },
  en: {
    htmlLang: "en",
    eyebrow: "Local Prototype",
    title: "OA Home Pain Check-in",
    disclaimer: "Research prototype -- not approved for clinical use.",
    language: "Language",
    ready: "Ready",
    starting: "Starting",
    listening: "Listening",
    processing: "Processing",
    speaking: "Speaking",
    complete: "Complete",
    urgentFlag: "Urgent flag",
    error: "Error",
    voiceUnavailable: "Voice unavailable",
    start: "Start Check-in",
    restart: "Restart Check-in",
    mic: "Mic",
    micStartLabel: "Start voice input",
    micStopLabel: "Stop voice input",
    inputPlaceholder: "Type an answer or use the microphone",
    inputAria: "Message",
    send: "Send",
    sendAria: "Send answer",
    stateTitle: "Check-in State",
    step: "Step",
    pain: "Pain",
    redFlags: "Red Flags",
    identity: "Identity",
    report: "Doctor Report",
    save: "Save",
    notStarted: "Not started",
    notCaptured: "Not captured",
    notScreened: "Not screened",
    notConfirmed: "Not confirmed",
    noUrgentFlags: "No urgent red flags",
    uncertain: "Uncertain",
    yes: "Yes",
    reportPending: "The report will appear here after the check-in is complete.",
    systemIntro: "This local prototype supports typed input and browser voice input when available. Start a check-in when ready.",
    voiceUnavailableMessage: "Voice input was not available. You can continue by typing.",
    savedPrefix: "Report saved to ",
    saveFailed: "Could not save the report.",
    sessionNotStarted: "Start a check-in first.",
    stepLabels: {},
  },
};

const ui = () => UI[currentLanguage] || UI.en;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = currentLanguage;

  recognition.addEventListener("start", () => {
    recognizing = true;
    voiceButton.classList.add("listening");
    voiceButton.setAttribute("aria-label", ui().micStopLabel);
    setStatus(ui().listening, "active");
  });

  recognition.addEventListener("end", () => {
    recognizing = false;
    voiceButton.classList.remove("listening");
    voiceButton.setAttribute("aria-label", ui().micStartLabel);
    if (!lastState?.complete && !assistantSpeaking) {
      setStatus(ui().ready, "active");
    }
  });

  recognition.addEventListener("result", (event) => {
    const result = event.results[event.results.length - 1][0].transcript;
    messageInput.value = result;
    messageInput.focus();
    if (autoVoiceEnabled && sessionId && !lastState?.complete) {
      window.setTimeout(() => {
        const text = messageInput.value.trim();
        if (text) {
          messageInput.value = "";
          sendMessage(text);
        }
      }, 250);
    }
  });

  recognition.addEventListener("error", () => {
    addMessage("system", ui().voiceUnavailableMessage);
    setStatus(ui().voiceUnavailable, "warning");
  });
} else {
  voiceButton.disabled = true;
  voiceButton.title = ui().voiceUnavailable;
}

startButton.addEventListener("click", async () => {
  await startSession();
});

languageSelect.addEventListener("change", () => {
  currentLanguage = languageSelect.value;
  selectedVoice = null;
  if (recognition && !recognizing) {
    recognition.lang = currentLanguage;
  }
  applyLanguage();
});

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !sessionId) {
    return;
  }
  messageInput.value = "";
  await sendMessage(text);
});

voiceButton.addEventListener("click", () => {
  if (!recognition || !sessionId) {
    return;
  }
  if (recognizing) {
    autoVoiceEnabled = false;
    recognition.stop();
    return;
  }
  autoVoiceEnabled = true;
  startListening();
});

saveReportButton.addEventListener("click", async () => {
  if (!sessionId) {
    return;
  }
  const response = await fetch("/api/save_report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  const payload = await response.json();
  if (payload.saved) {
    addMessage("system", `Report saved to ${payload.path}`);
  } else {
    addMessage("system", payload.error || "Could not save the report.");
  }
});

async function startSession() {
  setStatus(ui().starting, "active");
  autoVoiceEnabled = true;
  stopCurrentSpeech();
  window.speechSynthesis?.cancel();
  const response = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: currentLanguage }),
  });
  const payload = await response.json();
  sessionId = payload.session_id;
  transcriptEl.innerHTML = "";
  startButton.textContent = ui().restart;
  messageInput.disabled = false;
  sendButton.disabled = false;
  voiceButton.disabled = !recognition;
  updateState(payload.state);
  renderAssistantMessages(payload.assistant_messages || []);
  messageInput.focus();
}

async function sendMessage(text) {
  addMessage("user", text);
  setStatus(ui().processing, "active");
  const response = await fetch("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  const payload = await response.json();
  if (!response.ok) {
    addMessage("system", payload.error || ui().error);
    setStatus(ui().error, "warning");
    return;
  }
  updateState(payload.state);
  renderAssistantMessages(payload.assistant_messages || []);
  messageInput.focus();
}

function renderAssistantMessages(messages) {
  for (const message of messages) {
    addMessage("assistant", message);
  }
  speakQueue(messages);
}

function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  transcriptEl.appendChild(message);
  scrollTranscriptToBottom();
}

function updateState(state) {
  lastState = state;
  stepValue.textContent = labelizeStep(state.step);
  painValue.textContent =
    state.pain?.score === null || state.pain?.score === undefined
      ? ui().notCaptured
      : `24h ${state.pain.average_24h_score ?? "?"}/10; now ${state.pain.score}/10 (${state.pain.severity})`;
  redFlagValue.textContent = state.safety?.red_flag_present
    ? `${ui().yes}: ${state.safety.red_flag_symptoms.join(", ")}`
    : state.safety?.red_flag_uncertain
      ? ui().uncertain
      : ui().noUrgentFlags;
  identityValue.textContent = state.identity?.status || ui().notConfirmed;

  if (state.report) {
    reportOutput.textContent = state.report;
    saveReportButton.disabled = false;
  } else {
    reportOutput.textContent = ui().reportPending;
    saveReportButton.disabled = true;
  }

  if (state.safety?.red_flag_present) {
    setStatus(ui().urgentFlag, "danger");
  } else if (state.complete) {
    setStatus(ui().complete, "active");
    sendButton.disabled = true;
    messageInput.disabled = true;
    voiceButton.disabled = true;
  } else {
    setStatus(ui().ready, "active");
  }
}

function setStatus(text, tone = "idle") {
  statusText.textContent = text;
  statusDot.className = `status-dot ${tone}`;
}

async function speakQueue(messages) {
  if (!messages.length) {
    maybeStartAutoListening();
    return;
  }
  const [first, ...rest] = messages;
  await speak(first);
  speakQueue(rest);
}

async function speak(text) {
  assistantSpeaking = true;
  setStatus(ui().speaking, "active");
  try {
    const playedLocal = await speakWithLocalTts(text);
    if (!playedLocal) {
      await speakWithBrowserTts(text);
    }
  } finally {
    assistantSpeaking = false;
  }
}

async function speakWithLocalTts(text) {
  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: currentLanguage }),
    });
    if (!response.ok) {
      return false;
    }
    const blob = await response.blob();
    if (!blob.size) {
      return false;
    }
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    activeAudio = audio;
    await new Promise((resolve, reject) => {
      audio.onended = resolve;
      audio.onerror = reject;
      audio.play().catch(reject);
    });
    URL.revokeObjectURL(audioUrl);
    if (activeAudio === audio) {
      activeAudio = null;
    }
    return true;
  } catch (error) {
    return false;
  }
}

function speakWithBrowserTts(text) {
  if (!("speechSynthesis" in window)) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92;
    utterance.pitch = 1.08;
    const voice = getPreferredVoice();
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    utterance.onend = resolve;
    utterance.onerror = resolve;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  });
}

function stopCurrentSpeech() {
  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.currentTime = 0;
    } catch (error) {
      // Ignore audio cleanup errors; the next utterance will create a new element.
    }
    activeAudio = null;
  }
  window.speechSynthesis?.cancel();
}

function getPreferredVoice() {
  if (selectedVoice) {
    return selectedVoice;
  }
  if (!("speechSynthesis" in window)) {
    return null;
  }
  const voices = window.speechSynthesis.getVoices();
  const preferredNames =
    currentLanguage === "zh-CN"
      ? ["Ting-Ting", "Mei-Jia", "Sin-Ji", "Microsoft Xiaoxiao", "Microsoft Huihui", "Google 普通话", "Chinese", "Mandarin"]
      : [
          "Samantha",
          "Victoria",
          "Karen",
          "Moira",
          "Tessa",
          "Microsoft Aria",
          "Microsoft Jenny",
          "Google UK English Female",
          "Google US English",
          "Female",
        ];
  selectedVoice =
    preferredNames
      .map((name) => voices.find((voice) => voice.name.toLowerCase().includes(name.toLowerCase())))
      .find(Boolean) ||
    (currentLanguage === "zh-CN"
      ? voices.find((voice) => /zh|chinese|mandarin|xiaoxiao|huihui|ting/i.test(`${voice.lang} ${voice.name}`))
      : voices.find((voice) => /female|woman|samantha|victoria|jenny|aria|karen/i.test(voice.name))) ||
    voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith(currentLanguage.toLowerCase().slice(0, 2))) ||
    voices[0] ||
    null;
  return selectedVoice;
}

if ("speechSynthesis" in window) {
  window.speechSynthesis.addEventListener("voiceschanged", () => {
    selectedVoice = null;
    getPreferredVoice();
  });
  getPreferredVoice();
}

function maybeStartAutoListening() {
  if (!autoVoiceEnabled || !recognition || !sessionId || lastState?.complete || recognizing) {
    return;
  }
  window.setTimeout(() => {
    if (!assistantSpeaking && !recognizing && !lastState?.complete) {
      startListening();
    }
  }, 350);
}

function startListening() {
  if (!recognition || recognizing || assistantSpeaking || lastState?.complete) {
    return;
  }
  try {
    recognition.lang = currentLanguage;
    recognition.start();
  } catch (error) {
    setStatus(ui().ready, "active");
  }
}

function scrollTranscriptToBottom() {
  requestAnimationFrame(() => {
    const lastMessage = transcriptEl.lastElementChild;
    if (!lastMessage) {
      return;
    }
    lastMessage.scrollIntoView({ block: "end", behavior: "smooth" });
    window.setTimeout(() => {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
    }, 80);
  });
}

function labelizeStep(step) {
  if (!step) {
    return ui().notStarted;
  }
  if (ui().stepLabels[step]) {
    return ui().stepLabels[step];
  }
  return step
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function applyLanguage() {
  const text = ui();
  document.documentElement.lang = text.htmlLang;
  eyebrowText.textContent = text.eyebrow;
  appTitle.textContent = text.title;
  disclaimerText.textContent = text.disclaimer;
  languageLabel.textContent = text.language;
  startButton.textContent = sessionId ? text.restart : text.start;
  voiceButton.querySelector("span").textContent = text.mic;
  voiceButton.setAttribute("aria-label", text.micStartLabel);
  voiceButton.title = text.micStartLabel;
  messageInput.placeholder = text.inputPlaceholder;
  messageInput.setAttribute("aria-label", text.inputAria);
  sendButton.querySelector("span").textContent = text.send;
  sendButton.setAttribute("aria-label", text.sendAria);
  sendButton.title = text.sendAria;
  stateTitle.textContent = text.stateTitle;
  stepLabel.textContent = text.step;
  painLabel.textContent = text.pain;
  redFlagLabel.textContent = text.redFlags;
  identityLabel.textContent = text.identity;
  reportTitle.textContent = text.report;
  saveReportButton.textContent = text.save;
  if (!sessionId) {
    stepValue.textContent = text.notStarted;
    painValue.textContent = text.notCaptured;
    redFlagValue.textContent = text.notScreened;
    identityValue.textContent = text.notConfirmed;
    reportOutput.textContent = text.reportPending;
    setStatus(text.ready, "idle");
    transcriptEl.innerHTML = "";
    addMessage("system", text.systemIntro);
  } else if (lastState) {
    updateState(lastState);
  }
  if (recognition && !recognizing) {
    recognition.lang = currentLanguage;
  }
}

applyLanguage();
