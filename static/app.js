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
let mediaRecorder = null;
let recordedChunks = [];
let autoVoiceEnabled = true;
let submitStoppedRecording = false;
let assistantSpeaking = false;
let selectedVoice = null;
let currentLanguage = "zh-CN";
let activeAudio = null;
let activeSpeechResolve = null;
let speechGeneration = 0;
let voiceStatus = null;
let voiceStatusPromise = null;
let localSttUsable = false;
let localTtsUsable = false;
let localSttFailed = false;
let localTtsFailed = false;
let preferLocalStt = false;
let preferLocalTts = false;

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
    voiceRetryBrowser: "本地语音识别不可用，已切换到浏览器语音输入。",
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
    voiceRetryBrowser: "Local speech recognition was unavailable, so I switched to browser voice input.",
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
  voiceButton.disabled = !navigator.mediaDevices?.getUserMedia;
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
  cancelAssistantSpeech();
  messageInput.value = "";
  await sendMessage(text);
});

messageInput.addEventListener("input", () => {
  if (assistantSpeaking && messageInput.value.trim()) {
    cancelAssistantSpeech();
    setStatus(ui().ready, "active");
  }
});

voiceButton.addEventListener("click", () => {
  if (!sessionId) {
    return;
  }
  if (recognizing) {
    autoVoiceEnabled = false;
    submitStoppedRecording = true;
    stopListening();
    return;
  }
  autoVoiceEnabled = true;
  if (assistantSpeaking) {
    cancelAssistantSpeech();
  }
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
  await loadVoiceStatus();
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
  voiceButton.disabled = !(recognition || canUseLocalStt());
  updateState(payload.state);
  renderAssistantMessages(payload.assistant_messages || []);
  messageInput.focus();
}

async function sendMessage(text) {
  cancelAssistantSpeech();
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
  const generation = ++speechGeneration;
  for (const message of messages) {
    addMessage("assistant", message);
  }
  speakQueue(messages, generation);
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

async function speakQueue(messages, generation = speechGeneration) {
  if (generation !== speechGeneration) {
    return;
  }
  if (!messages.length) {
    maybeStartAutoListening(generation);
    return;
  }
  const [first, ...rest] = messages;
  await speak(first, generation);
  if (generation === speechGeneration) {
    speakQueue(rest, generation);
  }
}

async function speak(text, generation = speechGeneration) {
  if (generation !== speechGeneration) {
    return;
  }
  assistantSpeaking = true;
  setStatus(ui().speaking, "active");
  try {
    if (preferLocalTts && canUseLocalTts()) {
      const playedLocal = await speakWithLocalTts(text, generation);
      if (!playedLocal && generation === speechGeneration) {
        await speakWithBrowserTts(text, generation);
      }
      return;
    }
    const playedBrowser = await speakWithBrowserTts(text, generation);
    if (!playedBrowser && generation === speechGeneration && canUseLocalTts()) {
      await speakWithLocalTts(text, generation);
    }
  } finally {
    if (generation === speechGeneration) {
      assistantSpeaking = false;
    }
  }
}

async function speakWithLocalTts(text, generation = speechGeneration) {
  if (localTtsFailed || !canUseLocalTts()) {
    return false;
  }
  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: currentLanguage }),
    });
    if (!response.ok) {
      localTtsFailed = true;
      return false;
    }
    const blob = await response.blob();
    if (!blob.size) {
      return false;
    }
    if (generation !== speechGeneration) {
      return true;
    }
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    activeAudio = audio;
    await new Promise((resolve, reject) => {
      activeSpeechResolve = resolve;
      audio.onended = resolve;
      audio.onerror = reject;
      audio.play().catch(reject);
    });
    activeSpeechResolve = null;
    URL.revokeObjectURL(audioUrl);
    if (activeAudio === audio) {
      activeAudio = null;
    }
    return true;
  } catch (error) {
    localTtsFailed = true;
    return false;
  }
}

function speakWithBrowserTts(text, generation = speechGeneration) {
  if (!("speechSynthesis" in window)) {
    return Promise.resolve(false);
  }
  return new Promise((resolve) => {
    if (generation !== speechGeneration) {
      resolve(true);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92;
    utterance.pitch = 1.08;
    const voice = getPreferredVoice();
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    activeSpeechResolve = resolve;
    utterance.onend = () => resolve(true);
    utterance.onerror = () => resolve(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  });
}

function cancelAssistantSpeech() {
  speechGeneration += 1;
  stopCurrentSpeech();
  assistantSpeaking = false;
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
  if (activeSpeechResolve) {
    activeSpeechResolve();
    activeSpeechResolve = null;
  }
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

function maybeStartAutoListening(generation = speechGeneration) {
  if (!autoVoiceEnabled || !(recognition || canUseLocalStt()) || !sessionId || lastState?.complete || recognizing) {
    return;
  }
  window.setTimeout(() => {
    if (generation === speechGeneration && !assistantSpeaking && !recognizing && !lastState?.complete) {
      startListening();
    }
  }, 350);
}

async function startListening() {
  if (recognizing || lastState?.complete) {
    return;
  }
  if (assistantSpeaking) {
    cancelAssistantSpeech();
  }
  await loadVoiceStatus();
  if (shouldUseBrowserRecognition()) {
    startBrowserRecognition();
    return;
  }
  if (canUseLocalStt()) {
    await startLocalRecording();
    return;
  }
  startBrowserRecognition();
}

function startBrowserRecognition() {
  if (!recognition) {
    addMessage("system", ui().voiceUnavailableMessage);
    setStatus(ui().voiceUnavailable, "warning");
    return;
  }
  try {
    recognition.lang = currentLanguage;
    recognition.start();
  } catch (error) {
    setStatus(ui().ready, "active");
  }
}

function stopListening() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    return;
  }
  if (recognition) {
    recognition.stop();
  }
}

async function startLocalRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size) {
        recordedChunks.push(event.data);
      }
    };
    mediaRecorder.onstart = () => {
      recognizing = true;
      submitStoppedRecording = true;
      voiceButton.classList.add("listening");
      voiceButton.setAttribute("aria-label", ui().micStopLabel);
      setStatus(ui().listening, "active");
    };
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      recognizing = false;
      voiceButton.classList.remove("listening");
      voiceButton.setAttribute("aria-label", ui().micStartLabel);
      const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      const shouldSubmit = submitStoppedRecording;
      submitStoppedRecording = false;
      if (shouldSubmit && blob.size) {
        await transcribeAndSend(blob);
      }
      if (!lastState?.complete && !assistantSpeaking) {
        setStatus(ui().ready, "active");
      }
    };
    mediaRecorder.start();
  } catch (error) {
    localSttFailed = true;
    if (recognition) {
      addMessage("system", ui().voiceRetryBrowser);
      startBrowserRecognition();
      return;
    }
    addMessage("system", ui().voiceUnavailableMessage);
    setStatus(ui().voiceUnavailable, "warning");
  }
}

async function transcribeAndSend(blob) {
  cancelAssistantSpeech();
  setStatus(ui().processing, "active");
  const response = await fetch("/api/stt", {
    method: "POST",
    headers: {
      "Content-Type": blob.type || "audio/webm",
      "X-Language": currentLanguage,
      "X-Filename": "speech.webm",
    },
    body: blob,
  });
  const payload = await response.json();
  if (!response.ok || !payload.text) {
    localSttFailed = true;
    if (recognition) {
      addMessage("system", ui().voiceRetryBrowser);
      startBrowserRecognition();
    } else {
      addMessage("system", payload.error || ui().voiceUnavailableMessage);
      setStatus(ui().voiceUnavailable, "warning");
    }
    return;
  }
  messageInput.value = payload.text;
  messageInput.focus();
  if (autoVoiceEnabled && sessionId && !lastState?.complete) {
    messageInput.value = "";
    await sendMessage(payload.text);
  }
}

async function loadVoiceStatus() {
  if (voiceStatus || voiceStatusPromise) {
    return voiceStatusPromise || voiceStatus;
  }
  voiceStatusPromise = fetch("/api/voice_status")
    .then((response) => (response.ok ? response.json() : null))
    .then((status) => {
      voiceStatus = status;
      localSttUsable = Boolean(status?.stt?.model_path_found);
      localTtsUsable = Boolean(status?.tts?.openai?.tts_enabled || status?.tts?.kokoro_fallback_enabled);
      preferLocalStt = Boolean(status?.stt?.prefer_local);
      preferLocalTts = Boolean(status?.tts?.prefer_local);
      return status;
    })
    .catch(() => null)
    .finally(() => {
      voiceStatusPromise = null;
    });
  return voiceStatusPromise;
}

function canUseLocalStt() {
  return Boolean(preferLocalStt && navigator.mediaDevices?.getUserMedia && window.MediaRecorder && localSttUsable && !localSttFailed);
}

function canUseLocalTts() {
  return Boolean(preferLocalTts && localTtsUsable && !localTtsFailed);
}

function shouldUseBrowserRecognition() {
  return Boolean(recognition && (!preferLocalStt || !canUseLocalStt()));
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
