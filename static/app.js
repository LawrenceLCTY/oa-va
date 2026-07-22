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
const callHint = document.querySelector("#callHint");
const orb = document.querySelector("#orb");
const conversationPanel = document.querySelector(".call-panel");
const callModeLabel = document.querySelector("#callModeLabel");
const reportVisual = document.querySelector("#reportVisual");
const reportToggleButton = document.querySelector("#reportToggleButton");
const copyReportButton = document.querySelector("#copyReportButton");
const reportSummaryBand = document.querySelector("#reportSummaryBand");
const progressItems = Array.from(document.querySelectorAll(".progress-item"));
const voiceMeter = document.querySelector("#voiceMeter");
const meterBars = Array.from(document.querySelectorAll("#voiceMeter span"));
const turnStatusText = document.querySelector("#turnStatusText");
const recordingTimer = document.querySelector("#recordingTimer");

const REALTIME_URL = "https://api.openai.com/v1/realtime";

let sessionId = null;
let lastState = null;
let peerConnection = null;
let dataChannel = null;
let localStream = null;
let remoteAudio = null;
let callActive = false;
let currentLanguage = "zh-CN";
let pendingAssistantText = "";
let pendingUserText = "";
let pendingFunctionCalls = new Map();
let handledFunctionCalls = new Set();
let fallbackMode = false;
let serverVoiceFallback = false;
let privateMode = false;
let privateRecorder = null;
let privateAudioChunks = [];
let privateTranscriptDraft = "";
let discardPrivateRecording = false;
let recognition = null;
let recognizing = false;
let selectedVoice = null;
let fallbackAudio = null;
let fallbackAudioUrl = null;
let fallbackAudioResolve = null;
let browserSpeechResolve = null;
let privateVadSpeechDetected = false;
let privateVadSilentSince = null;
let privateVadStartedAt = 0;
let privateAutoStopTimer = null;
let serverTtsFailureCount = 0;
let audioContext = null;
let audioAnalyser = null;
let audioMeterFrame = null;
let audioMeterData = null;
let recordingStartedAt = null;
let recordingTimerId = null;

const UI = {
  "zh-CN": {
    htmlLang: "zh-CN",
    eyebrow: "私有语音随访原型",
    title: "骨关节炎疼痛随访",
    disclaimer: "研究原型：尚未批准用于临床。",
    language: "语言",
    ready: "准备就绪",
    connecting: "正在连接",
    listening: "正在听",
    speaking: "正在说话",
    processing: "处理中",
    complete: "已完成",
    urgentFlag: "紧急标记",
    error: "错误",
    start: "开始语音随访",
    restart: "重新开始",
    end: "结束",
    recordTurn: "开始回答",
    stopTurn: "结束回答",
    speak: "说话",
    stopMic: "停止",
    callReady: "准备好后开始语音随访。",
    callConnecting: "正在启动私有语音流水线...",
    callLive: "请说完一句完整回答后结束录音。",
    callEnded: "通话已结束。",
    realtimeUnavailable: "实时语音不可用，正在使用本地语音随访。",
    fallbackStarted: "已切换到基础本地随访模式。",
    privateStarted: "已进入 v0.7 私有可解释语音流水线。请按“开始回答”，说完后按“结束回答”。",
    privateUnavailable: "私有语音流水线暂不可用，正在使用基础本地随访。",
    privateRecordHint: "按“开始回答”后说一句完整回答；系统会用本地语音识别和规则引擎处理。",
    turnIdle: "每次回答一句完整内容",
    turnRecording: "正在录音，请自然说话",
    turnProcessing: "正在整理你的回答",
    browserFallbackStarted: "服务器语音暂不可用，本次使用浏览器语音。",
    micUnavailable: "无法打开麦克风。请检查浏览器权限。",
    inputPlaceholder: "需要时可输入补充回答",
    inputAria: "补充回答",
    send: "发送",
    sendAria: "发送补充回答",
    json: "JSON",
    preview: "预览",
    copy: "复制",
    copied: "报告已复制。",
    copyFailed: "无法复制报告。",
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
    eyebrow: "Private Voice Prototype",
    title: "OA Home Pain Check-in",
    disclaimer: "Research prototype -- not approved for clinical use.",
    language: "Language",
    ready: "Ready",
    connecting: "Connecting",
    listening: "Listening",
    speaking: "Speaking",
    processing: "Processing",
    complete: "Complete",
    urgentFlag: "Urgent flag",
    error: "Error",
    start: "Start Voice Check-in",
    restart: "Restart",
    end: "End",
    recordTurn: "Start Answer",
    stopTurn: "Stop Answer",
    speak: "Speak",
    stopMic: "Stop",
    callReady: "Start when you are ready to speak.",
    callConnecting: "Starting private voice pipeline...",
    callLive: "Speak one complete answer, then stop recording.",
    callEnded: "Call ended.",
    realtimeUnavailable: "Realtime voice is unavailable, using local voice check-in.",
    fallbackStarted: "Switched to the basic local check-in mode.",
    privateStarted: "v0.7 private explainable voice pipeline is active. Press Start Answer, speak one complete answer, then stop.",
    privateUnavailable: "Private voice pipeline is unavailable, so I switched to the basic local check-in.",
    privateRecordHint: "Press Start Answer, speak one complete answer, then stop. Local STT and the rule engine will process it.",
    turnIdle: "One complete answer per turn",
    turnRecording: "Recording now. Speak naturally",
    turnProcessing: "Processing your answer",
    browserFallbackStarted: "Server voice is temporarily unavailable, using browser voice for this response.",
    micUnavailable: "Could not open the microphone. Check browser permissions.",
    inputPlaceholder: "Type a backup answer if needed",
    inputAria: "Backup answer",
    send: "Send",
    sendAria: "Send backup answer",
    json: "JSON",
    preview: "Preview",
    copy: "Copy",
    copied: "Report copied.",
    copyFailed: "Could not copy report.",
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
    setCallMode("listening");
  });
  recognition.addEventListener("end", () => {
    recognizing = false;
    if (privateMode && privateRecorder?.state === "recording" && privateTranscriptDraft.trim()) {
      schedulePrivateAutoStop(350);
      return;
    }
    if (fallbackMode && !lastState?.complete) {
      stopVoiceMeter();
      resetTurnStatus();
      setButtonLabel(voiceButton, ui().speak);
      setCallMode("ready");
    }
  });
  recognition.addEventListener("result", (event) => {
    const texts = Array.from(event.results)
      .slice(event.resultIndex)
      .filter((result) => result.isFinal)
      .map((result) => result[0].transcript.trim())
      .filter(Boolean);
    const text = texts.join(" ").trim();
    if (text) {
      if (privateMode) {
        privateTranscriptDraft = `${privateTranscriptDraft} ${text}`.trim();
        schedulePrivateAutoStop(450);
        return;
      }
      messageInput.value = "";
      addMessage("user", text);
      submitTypedAnswer(text);
    }
  });
}

startButton.addEventListener("click", async () => {
  await startPrivateCall();
});

voiceButton.addEventListener("click", () => {
  if (privateMode) {
    togglePrivateTurnRecording();
    return;
  }
  if (fallbackMode) {
    toggleFallbackMic();
    return;
  }
  endRealtimeCall();
});

languageSelect.addEventListener("change", () => {
  if (callActive) {
    endRealtimeCall();
  }
  currentLanguage = languageSelect.value;
  applyLanguage();
});

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !sessionId) {
    return;
  }
  messageInput.value = "";
  addMessage("user", text);
  await submitTypedAnswer(text);
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
  addMessage("system", payload.saved ? `${ui().savedPrefix}${payload.path}` : payload.error || ui().saveFailed);
});

reportToggleButton?.addEventListener("click", () => {
  if (!lastState?.report) {
    return;
  }
  const showingJson = reportOutput.hidden;
  reportOutput.hidden = !showingJson;
  reportVisual.hidden = showingJson;
  if (reportSummaryBand) {
    reportSummaryBand.hidden = showingJson;
  }
  reportToggleButton.classList.toggle("active", showingJson);
  reportToggleButton.textContent = showingJson ? ui().preview : ui().json;
});

copyReportButton?.addEventListener("click", async () => {
  if (!lastState?.report) {
    return;
  }
  try {
    await copyText(lastState.report);
    copyReportButton.textContent = ui().copied;
    setTimeout(() => {
      copyReportButton.textContent = ui().copy;
    }, 1400);
  } catch (error) {
    copyReportButton.textContent = ui().copyFailed;
    setTimeout(() => {
      copyReportButton.textContent = ui().copy;
    }, 1800);
  }
});

function copyText(text) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const ok = document.execCommand("copy");
  textarea.remove();
  return ok ? Promise.resolve() : Promise.reject(new Error("copy failed"));
}

async function startRealtimeCall() {
  if (callActive) {
    endRealtimeCall();
  }
  resetConversationUi();
  setCallMode("connecting");
  try {
    const startPayload = await createRealtimeSession();
    sessionId = startPayload.session_id;
    updateConversationLayout();
    updateState(startPayload.state);
    enableBackupInput(true);
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    await connectWebRtc(startPayload.realtime);
    callActive = true;
    voiceButton.disabled = false;
    languageSelect.disabled = true;
    setButtonLabel(startButton, ui().restart);
    setCallMode("listening");
  } catch (error) {
    console.error(error);
    endRealtimeCall({ keepTranscript: true });
    await startBaseFallback(error.message || ui().realtimeUnavailable);
  }
}

async function startBaseFallback(reason) {
  fallbackMode = true;
  serverVoiceFallback = true;
  resetConversationUi();
  setCallMode("connecting");
  const response = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: currentLanguage }),
  });
  const payload = await response.json();
  if (!response.ok) {
    addMessage("system", payload.error || reason || ui().realtimeUnavailable);
    setCallMode("error");
    return;
  }
  sessionId = payload.session_id;
  updateConversationLayout();
  updateState(payload.state);
  enableBackupInput(true);
  voiceButton.disabled = !recognition;
  setButtonLabel(voiceButton, recognition ? ui().speak : ui().end);
  languageSelect.disabled = true;
  setButtonLabel(startButton, ui().restart);
  addMessage("system", ui().fallbackStarted);
  for (const message of payload.assistant_messages || []) {
    addMessage("assistant", message);
  }
  await speakFallbackQueue(payload.assistant_messages || []);
  setCallMode(lastState?.complete ? "complete" : "ready");
}

async function startPrivateCall() {
  if (callActive) {
    endRealtimeCall();
  }
  resetConversationUi();
  privateMode = true;
  serverVoiceFallback = true;
  setCallMode("connecting");
  try {
    const response = await fetch("/api/private/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: currentLanguage }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || ui().privateUnavailable);
    }
    sessionId = payload.session_id;
    callActive = true;
    updateConversationLayout();
    updateState(payload.state);
    enableBackupInput(true);
    voiceButton.disabled = false;
    setButtonLabel(voiceButton, ui().recordTurn);
    languageSelect.disabled = true;
    setButtonLabel(startButton, ui().restart);
    addMessage("system", ui().privateStarted);
    for (const message of payload.assistant_messages || []) {
      addMessage("assistant", message);
    }
    await speakFallbackQueue(payload.assistant_messages || []);
    if (!(await autoListenForPrivateAnswer())) {
      stopVoiceMeter();
      resetTurnStatus();
      setCallMode(lastState?.complete ? "complete" : "ready");
    }
  } catch (error) {
    console.error(error);
    endRealtimeCall({ keepTranscript: true });
    await startBaseFallback(error.message || ui().privateUnavailable);
  }
}

async function createRealtimeSession() {
  const response = await fetch("/api/realtime/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: currentLanguage }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || ui().realtimeUnavailable);
  }
  return payload;
}

async function connectWebRtc(realtimeSession) {
  const clientSecret = realtimeSession?.client_secret?.value;
  if (!clientSecret) {
    throw new Error(ui().realtimeUnavailable);
  }

  peerConnection = new RTCPeerConnection();
  remoteAudio = new Audio();
  remoteAudio.autoplay = true;
  peerConnection.ontrack = (event) => {
    remoteAudio.srcObject = event.streams[0];
  };
  for (const track of localStream.getTracks()) {
    peerConnection.addTrack(track, localStream);
  }

  dataChannel = peerConnection.createDataChannel("oai-events");
  dataChannel.addEventListener("open", () => {
    configureRealtimeSession();
    requestInitialResponse();
  });
  dataChannel.addEventListener("message", (event) => {
    handleRealtimeEvent(JSON.parse(event.data));
  });

  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  const sdpResponse = await fetch(`${REALTIME_URL}?model=${encodeURIComponent(realtimeSession.model || "gpt-realtime")}`, {
    method: "POST",
    body: offer.sdp,
    headers: {
      Authorization: `Bearer ${clientSecret}`,
      "Content-Type": "application/sdp",
    },
  });
  if (!sdpResponse.ok) {
    throw new Error(ui().realtimeUnavailable);
  }
  const answer = { type: "answer", sdp: await sdpResponse.text() };
  await peerConnection.setRemoteDescription(answer);
}

function configureRealtimeSession() {
  sendRealtimeEvent({
    type: "session.update",
    session: {
      modalities: ["audio", "text"],
      input_audio_transcription: { model: "gpt-4o-mini-transcribe" },
      turn_detection: {
        type: "server_vad",
        threshold: 0.5,
        prefix_padding_ms: 300,
        silence_duration_ms: 650,
        create_response: true,
        interrupt_response: true,
      },
    },
  });
}

function requestInitialResponse() {
  sendRealtimeEvent({
    type: "response.create",
    response: {
      modalities: ["audio", "text"],
    },
  });
}

function sendRealtimeEvent(event) {
  if (dataChannel?.readyState === "open") {
    dataChannel.send(JSON.stringify(event));
  }
}

function handleRealtimeEvent(event) {
  switch (event.type) {
    case "input_audio_buffer.speech_started":
      setCallMode("listening");
      break;
    case "response.created":
      setCallMode("processing");
      break;
    case "response.audio.delta":
      setCallMode("speaking");
      break;
    case "response.audio_transcript.delta":
    case "response.text.delta":
      pendingAssistantText += event.delta || "";
      break;
    case "response.audio_transcript.done":
    case "response.text.done":
      flushAssistantText(event.transcript || event.text || pendingAssistantText);
      break;
    case "conversation.item.input_audio_transcription.completed":
      flushUserText(event.transcript || pendingUserText);
      break;
    case "response.function_call_arguments.delta":
      collectFunctionArguments(event);
      break;
    case "response.function_call_arguments.done":
      completeFunctionCall(event);
      break;
    case "response.output_item.done":
      completeOutputItem(event.item);
      break;
    case "response.done":
      setCallMode(lastState?.complete ? "complete" : "listening");
      break;
    case "error":
      addMessage("system", event.error?.message || ui().error);
      setCallMode("error");
      break;
    default:
      break;
  }
}

function collectFunctionArguments(event) {
  const callId = event.call_id;
  if (!callId) {
    return;
  }
  const current = pendingFunctionCalls.get(callId) || { name: event.name || "", arguments: "" };
  current.name = event.name || current.name;
  current.arguments += event.delta || "";
  pendingFunctionCalls.set(callId, current);
}

async function completeFunctionCall(event) {
  const callId = event.call_id;
  if (!callId || handledFunctionCalls.has(callId)) {
    return;
  }
  handledFunctionCalls.add(callId);
  const item = pendingFunctionCalls.get(callId) || { name: event.name || "", arguments: event.arguments || "" };
  pendingFunctionCalls.delete(callId);

  let args = {};
  try {
    args = JSON.parse(event.arguments || item.arguments || "{}");
  } catch (error) {
    args = {};
  }
  if (!args.session_id) {
    args.session_id = sessionId;
  }

  const result = await runClinicalTool(item.name || event.name || "submit_patient_answer", args);
  sendRealtimeEvent({
    type: "conversation.item.create",
    item: {
      type: "function_call_output",
      call_id: callId,
      output: JSON.stringify(result),
    },
  });

  if (!lastState?.complete) {
    sendRealtimeEvent({
      type: "response.create",
      response: {
        modalities: ["audio", "text"],
        instructions: result.spoken_instruction || `Continue the clinical check-in using this required next content: ${(result.assistant_messages || []).join(" ")}`,
      },
    });
  }
}

function completeOutputItem(item) {
  if (!item || item.type !== "function_call" || !item.call_id || handledFunctionCalls.has(item.call_id)) {
    return;
  }
  completeFunctionCall({
    call_id: item.call_id,
    name: item.name,
    arguments: item.arguments,
  });
}

async function runClinicalTool(name, args) {
  const response = await fetch("/api/realtime/tool", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, arguments: args }),
  });
  const payload = await response.json();
  if (!response.ok) {
    return { ok: false, error: payload.error || ui().error };
  }
  updateState(payload.state);
  return payload;
}

async function submitTypedAnswer(text) {
  setCallMode("processing");
  if (privateMode) {
    await submitFallbackAnswer(text);
    return;
  }
  if (fallbackMode) {
    await submitFallbackAnswer(text);
    return;
  }
  const result = await runClinicalTool("submit_patient_answer", { session_id: sessionId, answer: text });
  if (dataChannel?.readyState === "open") {
    sendRealtimeEvent({
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text }],
      },
    });
    sendRealtimeEvent({
      type: "response.create",
      response: {
        modalities: ["audio", "text"],
        instructions: result.spoken_instruction || `The patient typed a backup answer. Continue with this required next content: ${(result.assistant_messages || []).join(" ")}`,
      },
    });
  }
}

async function submitFallbackAnswer(text) {
  const response = await fetch("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  const payload = await response.json();
  if (!response.ok) {
    addMessage("system", payload.error || ui().error);
    setCallMode("error");
    return;
  }
  updateState(payload.state);
  for (const message of payload.assistant_messages || []) {
    addMessage("assistant", message);
  }
  await speakFallbackQueue(payload.assistant_messages || []);
  setCallMode(lastState?.complete ? "complete" : "ready");
}

async function speakFallbackQueue(messages) {
  const spokenText = (messages || []).map((message) => String(message || "").trim()).filter(Boolean).join(" ");
  if (spokenText) {
    await speakFallback(spokenText);
  }
}

async function autoListenForPrivateAnswer() {
  if (!privateMode || !sessionId || lastState?.complete) {
    return false;
  }
  return beginPrivateTurnRecording({ interruptSpeech: false });
}

function speakFallback(text) {
  if (serverVoiceFallback) {
    return speakServerTts(text);
  }
  return speakBrowserTts(text);
}

async function speakServerTts(text) {
  try {
    const requestStartedAt = performance.now();
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: currentLanguage }),
    });
    if (!response.ok) {
      throw new Error("server tts unavailable");
    }
    const ttsLatencyMs = response.headers.get("X-TTS-Latency-Ms");
    const ttsEngine = response.headers.get("X-TTS-Engine");
    const blob = await response.blob();
    serverTtsFailureCount = 0;
    console.debug("server tts", {
      engine: ttsEngine,
      serverLatencyMs: ttsLatencyMs,
      browserFetchMs: Math.round(performance.now() - requestStartedAt),
      bytes: blob.size,
    });
    const audioUrl = URL.createObjectURL(blob);
    stopAssistantSpeech();
    fallbackAudioUrl = audioUrl;
    fallbackAudio = new Audio(audioUrl);
    setCallMode("speaking");
    await new Promise((resolve) => {
      fallbackAudioResolve = resolve;
      const finish = () => {
        fallbackAudioResolve = null;
        if (fallbackAudioUrl) {
          URL.revokeObjectURL(fallbackAudioUrl);
          fallbackAudioUrl = null;
        }
        resolve();
      };
      fallbackAudio.onended = finish;
      fallbackAudio.onerror = finish;
      fallbackAudio.play().catch(finish);
    });
  } catch (error) {
    serverTtsFailureCount += 1;
    if (serverTtsFailureCount >= 2) {
      serverVoiceFallback = false;
    }
    addMessage("system", ui().browserFallbackStarted);
    await speakBrowserTts(text);
  }
}

function speakBrowserTts(text) {
  if (!("speechSynthesis" in window)) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92;
    utterance.pitch = 1.04;
    const voice = getPreferredVoice();
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = currentLanguage;
    }
    const finish = () => {
      browserSpeechResolve = null;
      resolve();
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    browserSpeechResolve = finish;
    window.speechSynthesis.cancel();
    setCallMode("speaking");
    window.speechSynthesis.speak(utterance);
  });
}

function stopAssistantSpeech() {
  if (fallbackAudio) {
    fallbackAudio.pause();
    fallbackAudio.removeAttribute("src");
    fallbackAudio.load();
    fallbackAudio = null;
  }
  if (fallbackAudioUrl) {
    URL.revokeObjectURL(fallbackAudioUrl);
    fallbackAudioUrl = null;
  }
  if (fallbackAudioResolve) {
    const resolve = fallbackAudioResolve;
    fallbackAudioResolve = null;
    resolve();
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  if (browserSpeechResolve) {
    const resolve = browserSpeechResolve;
    browserSpeechResolve = null;
    resolve();
  }
}

function stopPrivateTurnRecording() {
  if (!privateRecorder || privateRecorder.state !== "recording") {
    return;
  }
  clearPrivateAutoStop();
  privateRecorder.stop();
  stopVoiceMeter({ keepTimer: true });
  setTurnStatus(ui().turnProcessing);
  setButtonLabel(voiceButton, ui().recordTurn);
  if (recognition && recognizing) {
    recognition.stop();
  }
}

function schedulePrivateAutoStop(delayMs) {
  clearPrivateAutoStop();
  privateAutoStopTimer = setTimeout(() => {
    if (privateMode && privateRecorder?.state === "recording") {
      stopPrivateTurnRecording();
    }
  }, delayMs);
}

function clearPrivateAutoStop() {
  if (privateAutoStopTimer) {
    clearTimeout(privateAutoStopTimer);
    privateAutoStopTimer = null;
  }
}

function updatePrivateAutoEndpoint(level) {
  if (!privateMode || privateRecorder?.state !== "recording") {
    return;
  }
  const now = Date.now();
  if (!privateVadStartedAt) {
    privateVadStartedAt = now;
  }
  const speechThreshold = 14;
  const silenceThreshold = 8;
  if (level >= speechThreshold) {
    privateVadSpeechDetected = true;
    privateVadSilentSince = null;
    return;
  }
  if (!privateVadSpeechDetected || now - privateVadStartedAt < 900 || level > silenceThreshold) {
    return;
  }
  if (!privateVadSilentSince) {
    privateVadSilentSince = now;
    return;
  }
  if (now - privateVadSilentSince >= 1400) {
    stopPrivateTurnRecording();
  }
}

function toggleFallbackMic() {
  if (!recognition || !sessionId || lastState?.complete) {
    return;
  }
  if (recognizing) {
    recognition.stop();
    stopVoiceMeter();
    resetTurnStatus();
    setButtonLabel(voiceButton, ui().speak);
    return;
  }
  try {
    recognition.lang = currentLanguage;
    recognition.start();
    startVoiceMeter(localStream);
    startRecordingTimer();
    setTurnStatus(ui().turnRecording);
    setButtonLabel(voiceButton, ui().stopMic);
  } catch (error) {
    setCallMode("ready");
  }
}

async function togglePrivateTurnRecording() {
  if (!sessionId || lastState?.complete) {
    return;
  }
  if (privateRecorder && privateRecorder.state === "recording") {
    stopPrivateTurnRecording();
    return;
  }
  await beginPrivateTurnRecording({ interruptSpeech: true });
}

async function beginPrivateTurnRecording(options = {}) {
  if (!sessionId || lastState?.complete) {
    return false;
  }
  if (privateRecorder && privateRecorder.state === "recording") {
    return true;
  }
  if (options.interruptSpeech !== false) {
    stopAssistantSpeech();
  }
  try {
    if (!localStream) {
      localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    }
    privateAudioChunks = [];
    privateTranscriptDraft = "";
    privateVadSpeechDetected = false;
    privateVadSilentSince = null;
    privateVadStartedAt = 0;
    const mimeType = preferredRecordingMimeType();
    privateRecorder = new MediaRecorder(localStream, mimeType ? { mimeType } : undefined);
    discardPrivateRecording = false;
    privateRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        privateAudioChunks.push(event.data);
      }
    });
    privateRecorder.addEventListener("stop", submitPrivateRecordedTurn);
    clearPrivateAutoStop();
    privateRecorder.start();
    startPrivateSpeechRecognition();
    startVoiceMeter(localStream);
    startRecordingTimer();
    setTurnStatus(ui().turnRecording);
    setButtonLabel(voiceButton, ui().stopTurn);
    setCallMode("listening");
    return true;
  } catch (error) {
    addMessage("system", ui().micUnavailable);
    setCallMode("error");
    return false;
  }
}

function startVoiceMeter(stream) {
  if (!voiceMeter || !meterBars.length) {
    return;
  }
  stopVoiceMeter({ keepTimer: true });
  if (!stream) {
    voiceMeter.classList.add("active");
    conversationPanel.classList.add("recording");
    meterBars.forEach((bar, index) => bar.style.setProperty("--level", `${10 + (index % 3) * 8}px`));
    return;
  }
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
      voiceMeter.classList.add("active");
      conversationPanel.classList.add("recording");
      return;
    }
    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    audioAnalyser = audioContext.createAnalyser();
    audioAnalyser.fftSize = 128;
    audioAnalyser.smoothingTimeConstant = 0.72;
    audioMeterData = new Uint8Array(audioAnalyser.frequencyBinCount);
    source.connect(audioAnalyser);
    voiceMeter.classList.add("active");
    conversationPanel.classList.add("recording");
    updateVoiceMeter();
  } catch (error) {
    voiceMeter.classList.add("active");
    conversationPanel.classList.add("recording");
  }
}

function updateVoiceMeter() {
  if (!audioAnalyser || !audioMeterData) {
    return;
  }
  audioAnalyser.getByteFrequencyData(audioMeterData);
  const groupSize = Math.max(1, Math.floor(audioMeterData.length / meterBars.length));
  let total = 0;
  meterBars.forEach((bar, index) => {
    const start = index * groupSize;
    const slice = audioMeterData.slice(start, start + groupSize);
    const average = slice.reduce((sum, value) => sum + value, 0) / Math.max(1, slice.length);
    total += average;
    const height = 8 + Math.min(30, Math.round((average / 255) * 34));
    bar.style.setProperty("--level", `${height}px`);
  });
  updatePrivateAutoEndpoint(total / Math.max(1, meterBars.length));
  audioMeterFrame = requestAnimationFrame(updateVoiceMeter);
}

function stopVoiceMeter(options = {}) {
  const keepTimer = Boolean(options.keepTimer);
  if (audioMeterFrame) {
    cancelAnimationFrame(audioMeterFrame);
    audioMeterFrame = null;
  }
  clearPrivateAutoStop();
  if (audioContext) {
    audioContext.close().catch(() => {});
  }
  audioContext = null;
  audioAnalyser = null;
  audioMeterData = null;
  voiceMeter?.classList.remove("active");
  conversationPanel?.classList.remove("recording");
  meterBars.forEach((bar) => bar.style.setProperty("--level", "8px"));
  if (!keepTimer) {
    stopRecordingTimer();
  }
}

function startRecordingTimer() {
  recordingStartedAt = Date.now();
  updateRecordingTimer();
  if (recordingTimerId) {
    clearInterval(recordingTimerId);
  }
  recordingTimerId = setInterval(updateRecordingTimer, 250);
}

function stopRecordingTimer() {
  if (recordingTimerId) {
    clearInterval(recordingTimerId);
    recordingTimerId = null;
  }
  recordingStartedAt = null;
  if (recordingTimer) {
    recordingTimer.textContent = "00:00";
  }
}

function updateRecordingTimer() {
  if (!recordingTimer || !recordingStartedAt) {
    return;
  }
  const elapsedSeconds = Math.floor((Date.now() - recordingStartedAt) / 1000);
  const minutes = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
  const seconds = String(elapsedSeconds % 60).padStart(2, "0");
  recordingTimer.textContent = `${minutes}:${seconds}`;
}

function setTurnStatus(text) {
  if (turnStatusText) {
    turnStatusText.textContent = text;
  }
}

function resetTurnStatus() {
  setTurnStatus(ui().turnIdle);
  stopRecordingTimer();
}

function preferredRecordingMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function startPrivateSpeechRecognition() {
  if (!recognition) {
    return;
  }
  try {
    recognition.lang = currentLanguage;
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.start();
  } catch (error) {
    return;
  }
}

async function submitPrivateRecordedTurn() {
  if (discardPrivateRecording) {
    discardPrivateRecording = false;
    privateAudioChunks = [];
    stopVoiceMeter();
    resetTurnStatus();
    setCallMode(sessionId ? "ready" : "ended");
    return;
  }
  if (!sessionId || !privateMode || !privateAudioChunks.length) {
    stopVoiceMeter();
    resetTurnStatus();
    setCallMode("ready");
    return;
  }
  stopVoiceMeter({ keepTimer: true });
  setTurnStatus(ui().turnProcessing);
  setCallMode("processing");
  const mimeType = privateRecorder?.mimeType || preferredRecordingMimeType() || "audio/webm";
  const blob = new Blob(privateAudioChunks, { type: mimeType });
  privateAudioChunks = [];
  const filename = mimeType.includes("ogg") ? "speech.ogg" : "speech.webm";
  try {
    const response = await fetch("/api/private/turn", {
      method: "POST",
      headers: {
        "Content-Type": mimeType,
        "X-Filename": filename,
        "X-Session-Id": sessionId,
        "X-Language": currentLanguage,
        "X-Transcript": encodeHeaderValue(privateTranscriptDraft),
      },
      body: blob,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || ui().privateUnavailable);
    }
    const transcript = payload.transcript || privateTranscriptDraft;
    if (transcript) {
      addMessage("user", transcript);
    }
    updateState(payload.state);
    for (const message of payload.assistant_messages || []) {
      addMessage("assistant", message);
    }
    await speakFallbackQueue(payload.assistant_messages || []);
    if (!(await autoListenForPrivateAnswer())) {
      stopVoiceMeter();
      resetTurnStatus();
      setCallMode(lastState?.complete ? "complete" : "ready");
    }
  } catch (error) {
    addMessage("system", error.message || ui().privateUnavailable);
    stopVoiceMeter();
    resetTurnStatus();
    setCallMode("error");
  }
}

function encodeHeaderValue(value) {
  return encodeURIComponent(value || "").slice(0, 1800);
}

function getPreferredVoice() {
  if (selectedVoice) {
    return selectedVoice;
  }
  if (!("speechSynthesis" in window)) {
    return null;
  }
  const voices = window.speechSynthesis.getVoices();
  selectedVoice =
    voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith(currentLanguage.toLowerCase().slice(0, 2))) ||
    voices[0] ||
    null;
  return selectedVoice;
}

function flushAssistantText(text) {
  const cleaned = (text || "").trim();
  pendingAssistantText = "";
  if (cleaned) {
    addMessage("assistant", cleaned);
  }
}

function flushUserText(text) {
  const cleaned = (text || "").trim();
  pendingUserText = "";
  if (cleaned) {
    addMessage("user", cleaned);
  }
}

function endRealtimeCall(options = {}) {
  const keepTranscript = Boolean(options.keepTranscript);
  callActive = false;
  if (!keepTranscript) {
    fallbackMode = false;
  }
  if (recognition && recognizing) {
    recognition.stop();
  }
  stopVoiceMeter();
  resetTurnStatus();
  pendingFunctionCalls.clear();
  handledFunctionCalls.clear();
  fallbackMode = false;
  serverVoiceFallback = false;
  privateMode = false;
  privateAudioChunks = [];
  privateTranscriptDraft = "";
  privateVadSpeechDetected = false;
  privateVadSilentSince = null;
  privateVadStartedAt = 0;
  if (privateRecorder && privateRecorder.state === "recording") {
    discardPrivateRecording = true;
    privateRecorder.stop();
  }
  privateRecorder = null;
  stopAssistantSpeech();
  if (dataChannel) {
    dataChannel.close();
    dataChannel = null;
  }
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (localStream) {
    localStream.getTracks().forEach((track) => track.stop());
    localStream = null;
  }
  if (remoteAudio) {
    remoteAudio.pause();
    remoteAudio.srcObject = null;
    remoteAudio = null;
  }
  voiceButton.disabled = true;
  setButtonLabel(voiceButton, ui().end);
  languageSelect.disabled = false;
  enableBackupInput(Boolean(sessionId && !lastState?.complete));
  if (!keepTranscript && sessionId && !lastState?.complete) {
    addMessage("system", ui().callEnded);
  }
  if (lastState?.complete) {
    setCallMode("complete");
  } else if (sessionId) {
    setCallMode("ended");
  } else {
    setCallMode("ready");
  }
  updateConversationLayout();
}

function resetConversationUi() {
  transcriptEl.innerHTML = "";
  sessionId = null;
  lastState = null;
  pendingAssistantText = "";
  pendingUserText = "";
  pendingFunctionCalls.clear();
  handledFunctionCalls.clear();
  stopVoiceMeter();
  resetTurnStatus();
  privateAudioChunks = [];
  privateTranscriptDraft = "";
  reportOutput.textContent = ui().reportPending;
  reportOutput.hidden = true;
  reportVisual.hidden = false;
  renderReportPreview(null);
  updateProgressRail(null);
  saveReportButton.disabled = true;
  if (reportToggleButton) {
    reportToggleButton.disabled = true;
    reportToggleButton.classList.remove("active");
    reportToggleButton.textContent = ui().json;
  }
  if (copyReportButton) {
    copyReportButton.disabled = true;
    copyReportButton.textContent = ui().copy;
  }
  stepValue.textContent = ui().notStarted;
  painValue.textContent = ui().notCaptured;
  redFlagValue.textContent = ui().notScreened;
  identityValue.textContent = ui().notConfirmed;
  enableBackupInput(false);
  updateConversationLayout();
}

function enableBackupInput(enabled) {
  messageInput.disabled = !enabled;
  sendButton.disabled = !enabled;
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
  updateConversationLayout();
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

  updateProgressRail(state);

  if (state.report) {
    reportOutput.textContent = state.report;
    renderReportPreview(state.report);
    saveReportButton.disabled = false;
    if (reportToggleButton) {
      reportToggleButton.disabled = false;
    }
    if (copyReportButton) {
      copyReportButton.disabled = false;
      copyReportButton.textContent = ui().copy;
    }
  } else {
    reportOutput.textContent = ui().reportPending;
    renderReportPreview(null);
    saveReportButton.disabled = true;
    if (reportToggleButton) {
      reportToggleButton.disabled = true;
      reportToggleButton.classList.remove("active");
      reportToggleButton.textContent = ui().json;
      reportOutput.hidden = true;
      reportVisual.hidden = false;
    }
    if (copyReportButton) {
      copyReportButton.disabled = true;
      copyReportButton.textContent = ui().copy;
    }
  }

  if (state.safety?.red_flag_present) {
    setCallMode("urgent");
  } else if (state.complete) {
    enableBackupInput(false);
    voiceButton.disabled = true;
    setCallMode("complete");
  }
}

function updateConversationLayout() {
  conversationPanel.classList.toggle("session-active", Boolean(sessionId));
}

function setButtonLabel(button, label) {
  const labelEl = button?.querySelector(".button-label") || button?.querySelector("span:last-child");
  if (labelEl) {
    labelEl.textContent = label;
  } else if (button) {
    button.textContent = label;
  }
}

function updateProgressRail(state) {
  const activeKey = progressKeyForStep(state?.step);
  const completed = completedProgressKeys(state);
  progressItems.forEach((item) => {
    const key = item.dataset.stepKey;
    item.classList.toggle("complete", completed.has(key));
    item.classList.toggle("current", key === activeKey && !state?.complete);
    item.classList.toggle("urgent", key === "red_flags" && Boolean(state?.safety?.red_flag_present));
  });
}

function progressKeyForStep(step) {
  if (!step) return "identity";
  if (["identity", "respondent_source", "readiness_hearing", "readiness_time", "permission"].includes(step)) return "identity";
  if (["average_pain_score", "current_pain_score", "pain_location"].includes(step)) return "pain";
  if (["functional_impact", "usual_comparison"].includes(step)) return "function";
  if (["treatment_context"].includes(step)) return "treatment";
  if (step.startsWith("side_effect") || ["medication_changed", "doctor_contacted", "emergency_visit"].includes(step)) return "side_effects";
  if (step === "red_flags") return "red_flags";
  if (step === "complete") return "complete";
  return "identity";
}

function completedProgressKeys(state) {
  const done = new Set();
  if (!state) return done;
  if (state.identity?.status && state.identity.status !== "missing") done.add("identity");
  if (state.pain?.score !== null && state.pain?.score !== undefined) done.add("pain");
  if (state.pain?.functional_impact || state.pain?.usual_comparison) done.add("function");
  if (state.safety?.medication_context) done.add("treatment");
  if (state.safety?.side_effect_screening_result && state.safety.side_effect_screening_result !== "unknown") done.add("side_effects");
  if (state.safety?.red_flag_present || state.safety?.red_flag_uncertain || state.step === "complete" || state.complete) done.add("red_flags");
  if (state.complete) done.add("complete");
  return done;
}

function renderReportPreview(reportText) {
  if (!reportVisual) return;
  if (!reportText) {
    reportSummaryBand.hidden = true;
    reportSummaryBand.innerHTML = "";
    reportVisual.className = "report-visual empty";
    reportVisual.textContent = ui().reportPending;
    return;
  }
  let report = null;
  try {
    report = JSON.parse(reportText);
  } catch (error) {
    reportSummaryBand.hidden = true;
    reportSummaryBand.innerHTML = "";
    reportVisual.className = "report-visual";
    reportVisual.textContent = reportText;
    return;
  }

  renderReportSummaryBand(report);
  reportVisual.className = "report-visual";
  reportVisual.innerHTML = "";

  const priorityText = String(report.suggested_follow_up_priority || report.follow_up_priority || report.doctor_summary || ui().report);
  const priority = document.createElement("div");
  priority.className = `report-priority ${isUrgentText(priorityText) ? "urgent" : ""}`;
  priority.append(createTextElement("span", "Follow-up priority"), document.createTextNode(priorityText));
  reportVisual.appendChild(priority);

  addChipRow([
    chip("Identity", report.medical_research_review?.clinical_completeness?.identity_complete),
    chip("Pain scores", report.medical_research_review?.clinical_completeness?.pain_scores_complete),
    chip("Function", report.medical_research_review?.clinical_completeness?.functional_anchor_complete),
    chip("Red flags", !(report.safety_assessment?.red_flag_present || report.safety_assessment?.red_flag_uncertain), report.safety_assessment?.red_flag_present ? "danger" : "warn"),
    chip("Study usable", report.medical_research_review?.research_quality?.usable_for_study),
  ]);

  addReportSection("Doctor handoff", [
    ["Summary", report.doctor_summary],
    ["Action advised", report.safety_assessment?.action_advised],
    ["Session", report.session?.conversation_type],
    ["Language", report.session?.language],
  ]);
  addReportSection("Patient", [
    ["Name", report.patient_identity?.name],
    ["Mobile", report.patient_identity?.mobile_number || report.patient_identity?.phone],
    ["Age", report.patient_identity?.age],
    ["Identity status", report.patient_identity?.status],
    ["Respondent", report.readiness?.respondent_source],
  ]);
  addReportSection("Pain assessment", [
    ["24h average", scoreWithSeverity(report.pain_assessment?.average_24h_score, report.pain_assessment?.average_24h_severity)],
    ["Current", scoreWithSeverity(report.pain_assessment?.current_score, report.pain_assessment?.current_severity)],
    ["Location", report.pain_assessment?.location],
    ["Functional impact", report.pain_assessment?.functional_impact],
    ["Usual baseline", report.pain_assessment?.usual_comparison],
    ["Patient words", report.pain_assessment?.patient_words],
  ]);
  addReportSection("Safety assessment", [
    ["Treatment context", report.safety_assessment?.medication_or_treatment_context],
    ["Side effects", report.safety_assessment?.side_effect_screening_result],
    ["Symptoms", listValue(report.safety_assessment?.reported_symptoms)],
    ["Symptom status", report.safety_assessment?.symptom_status],
    ["Symptom severity", report.safety_assessment?.symptom_severity],
    ["Medication changed", report.safety_assessment?.medication_reduced_paused_or_stopped],
    ["Doctor contacted", report.safety_assessment?.doctor_contacted],
    ["Emergency visit", report.safety_assessment?.emergency_visit_or_hospitalization],
    ["Red flags", report.safety_assessment?.red_flag_status],
    ["Red-flag symptoms", listValue(report.safety_assessment?.red_flag_symptoms)],
  ]);
  addReviewGrid("Research review", [
    ["Usable for study", yesNo(report.medical_research_review?.research_quality?.usable_for_study)],
    ["Requires callback", yesNo(report.medical_research_review?.research_quality?.requires_callback)],
    ["Missing fields", listValue(report.medical_research_review?.clinical_concerns?.missing_or_suspect_fields) || "None"],
    ["Review status", report.medical_research_review?.research_quality?.review_status],
  ]);
  addReviewGrid("Conversation quality", [
    ["Turns", report.conversation_trace?.turn_count],
    ["Model events", report.audit_metadata?.model_event_count],
    ["Observed models", listValue(report.audit_metadata?.model_names_observed) || "None"],
    ["Raw audio", report.audit_metadata?.raw_audio_retention],
  ]);
  addNoteList("Limitations", report.limitations);
}

function renderReportSummaryBand(report) {
  if (!reportSummaryBand) return;
  reportSummaryBand.hidden = false;
  reportSummaryBand.innerHTML = "";
  const priority = String(report.suggested_follow_up_priority || report.follow_up_priority || "Pending");
  const pain = scoreWithSeverity(report.pain_assessment?.current_score, report.pain_assessment?.current_severity) || "Not captured";
  const redFlags = report.safety_assessment?.red_flag_status || "unknown";
  reportSummaryBand.append(
    summaryPill("Priority", priority, isUrgentText(priority) ? "urgent" : ""),
    summaryPill("Current pain", pain),
    summaryPill("Red flags", redFlags, redFlags === "yes" ? "urgent" : ""),
  );
}

function summaryPill(label, value, tone = "") {
  const pill = document.createElement("div");
  pill.className = `summary-pill ${tone}`.trim();
  pill.append(createTextElement("span", label), createTextElement("strong", value || "-"));
  return pill;
}

function addChipRow(chips) {
  const row = document.createElement("div");
  row.className = "report-chip-row";
  chips.filter(Boolean).forEach((item) => row.appendChild(item));
  reportVisual.appendChild(row);
}

function chip(label, value, falseTone = "warn") {
  if (value === undefined || value === null) return null;
  const item = document.createElement("span");
  item.className = `report-chip ${value ? "good" : falseTone}`;
  item.textContent = `${label}: ${value ? "OK" : "Check"}`;
  return item;
}

function addReportSection(title, fields) {
  const section = document.createElement("section");
  section.className = "report-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.appendChild(heading);
  const dl = document.createElement("dl");
  for (const [label, value] of fields) {
    if (isEmptyReportValue(value)) continue;
    const row = document.createElement("div");
    row.className = "report-field";
    row.append(createTextElement("dt", label), createTextElement("dd", value));
    dl.appendChild(row);
  }
  section.appendChild(dl);
  reportVisual.appendChild(section);
}

function addReviewGrid(title, fields) {
  const section = document.createElement("section");
  section.className = "report-section";
  section.appendChild(createTextElement("h3", title));
  const grid = document.createElement("div");
  grid.className = "review-grid";
  fields.forEach(([label, value]) => {
    if (isEmptyReportValue(value)) return;
    const card = document.createElement("div");
    card.className = "review-card";
    card.append(createTextElement("span", label), createTextElement("strong", value));
    grid.appendChild(card);
  });
  section.appendChild(grid);
  reportVisual.appendChild(section);
}

function addNoteList(title, values) {
  if (!Array.isArray(values) || !values.length) return;
  const section = document.createElement("section");
  section.className = "report-section";
  section.appendChild(createTextElement("h3", title));
  const list = document.createElement("ul");
  list.className = "report-note-list";
  values.forEach((value) => {
    if (isEmptyReportValue(value)) return;
    const item = document.createElement("li");
    item.textContent = String(value);
    list.appendChild(item);
  });
  section.appendChild(list);
  reportVisual.appendChild(section);
}

function createTextElement(tag, text) {
  const el = document.createElement(tag);
  el.textContent = String(text ?? "");
  return el;
}

function isEmptyReportValue(value) {
  if (value === null || value === undefined || value === "") return true;
  if (Array.isArray(value) && !value.filter(Boolean).length) return true;
  return value === "none reported" || value === "未报告" || value === "unknown";
}

function listValue(value) {
  return Array.isArray(value) ? value.filter(Boolean).join(", ") : value;
}

function scoreWithSeverity(score, severity) {
  if (score === null || score === undefined) return "";
  return severity ? `${score}/10 (${severity})` : `${score}/10`;
}

function yesNo(value) {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return value;
}

function isUrgentText(text) {
  return /emergency|urgent|high priority|red flag|紧急|危险/i.test(String(text || ""));
}

function setCallMode(mode) {
  orb.className = `voice-orb ${mode}`;
  conversationPanel.classList.toggle("listening", mode === "listening" || mode === "speaking");
  if (mode === "connecting") {
    callHint.textContent = ui().callConnecting;
    callModeLabel.textContent = ui().connecting;
    setStatus(ui().connecting, "active");
  } else if (mode === "listening") {
    callHint.textContent = ui().callLive;
    callModeLabel.textContent = ui().listening;
    setStatus(ui().listening, "active");
  } else if (mode === "speaking") {
    callHint.textContent = ui().callLive;
    callModeLabel.textContent = ui().speaking;
    setStatus(ui().speaking, "active");
  } else if (mode === "processing") {
    callHint.textContent = ui().callLive;
    callModeLabel.textContent = ui().processing;
    setStatus(ui().processing, "active");
  } else if (mode === "complete") {
    callHint.textContent = ui().complete;
    callModeLabel.textContent = ui().complete;
    setStatus(ui().complete, "active");
  } else if (mode === "urgent") {
    callHint.textContent = ui().urgentFlag;
    callModeLabel.textContent = ui().urgentFlag;
    setStatus(ui().urgentFlag, "danger");
  } else if (mode === "error") {
    callHint.textContent = ui().realtimeUnavailable;
    callModeLabel.textContent = ui().error;
    setStatus(ui().error, "warning");
  } else if (mode === "ended") {
    callHint.textContent = ui().callEnded;
    callModeLabel.textContent = ui().ready;
    setStatus(ui().ready, "idle");
  } else {
    callHint.textContent = privateMode ? ui().privateRecordHint : ui().callReady;
    callModeLabel.textContent = ui().ready;
    setStatus(ui().ready, "idle");
  }
}

function setStatus(text, tone = "idle") {
  statusText.textContent = text;
  statusDot.className = `status-dot ${tone}`;
}

function scrollTranscriptToBottom() {
  requestAnimationFrame(() => {
    const lastMessage = transcriptEl.lastElementChild;
    if (lastMessage) {
      lastMessage.scrollIntoView({ block: "end", behavior: "smooth" });
    }
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
  setButtonLabel(startButton, sessionId ? text.restart : text.start);
  setButtonLabel(voiceButton, privateMode ? text.recordTurn : fallbackMode ? text.speak : text.end);
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
  if (!recordingStartedAt) {
    resetTurnStatus();
  }
  setButtonLabel(saveReportButton, text.save);
  if (reportToggleButton && !reportToggleButton.classList.contains("active")) {
    reportToggleButton.textContent = text.json;
  }
  if (copyReportButton && !lastState?.report) {
    copyReportButton.textContent = text.copy;
  }
  if (!sessionId) {
    resetConversationUi();
    setCallMode("ready");
  } else if (lastState) {
    updateState(lastState);
  }
  if (recognition && !recognizing) {
    recognition.lang = currentLanguage;
  }
}

applyLanguage();

if ("speechSynthesis" in window) {
  window.speechSynthesis.addEventListener("voiceschanged", () => {
    selectedVoice = null;
  });
}
