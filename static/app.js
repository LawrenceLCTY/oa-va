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

const UI = {
  "zh-CN": {
    htmlLang: "zh-CN",
    eyebrow: "实时语音原型",
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
    callReady: "准备好后开始语音随访。",
    callConnecting: "正在建立实时语音连接...",
    callLive: "可以直接说话。我会边听边回应。",
    callEnded: "通话已结束。",
    realtimeUnavailable: "实时语音不可用。请确认已设置 OPENAI_API_KEY。",
    micUnavailable: "无法打开麦克风。请检查浏览器权限。",
    inputPlaceholder: "需要时可输入补充回答",
    inputAria: "补充回答",
    send: "发送",
    sendAria: "发送补充回答",
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
    eyebrow: "Realtime Voice Prototype",
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
    callReady: "Start when you are ready to speak.",
    callConnecting: "Connecting realtime voice...",
    callLive: "You can speak naturally. I will listen and respond in real time.",
    callEnded: "Call ended.",
    realtimeUnavailable: "Realtime voice is unavailable. Check OPENAI_API_KEY.",
    micUnavailable: "Could not open the microphone. Check browser permissions.",
    inputPlaceholder: "Type a backup answer if needed",
    inputAria: "Backup answer",
    send: "Send",
    sendAria: "Send backup answer",
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

startButton.addEventListener("click", async () => {
  await startRealtimeCall();
});

voiceButton.addEventListener("click", () => {
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

async function startRealtimeCall() {
  if (callActive) {
    endRealtimeCall();
  }
  resetConversationUi();
  setCallMode("connecting");
  try {
    const startPayload = await createRealtimeSession();
    sessionId = startPayload.session_id;
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
    startButton.textContent = ui().restart;
    setCallMode("listening");
  } catch (error) {
    console.error(error);
    endRealtimeCall({ keepTranscript: true });
    addMessage("system", error.message || ui().realtimeUnavailable);
    setCallMode("error");
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
  pendingFunctionCalls.clear();
  handledFunctionCalls.clear();
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
}

function resetConversationUi() {
  transcriptEl.innerHTML = "";
  sessionId = null;
  lastState = null;
  pendingAssistantText = "";
  pendingUserText = "";
  pendingFunctionCalls.clear();
  handledFunctionCalls.clear();
  reportOutput.textContent = ui().reportPending;
  saveReportButton.disabled = true;
  stepValue.textContent = ui().notStarted;
  painValue.textContent = ui().notCaptured;
  redFlagValue.textContent = ui().notScreened;
  identityValue.textContent = ui().notConfirmed;
  enableBackupInput(false);
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
    setCallMode("urgent");
  } else if (state.complete) {
    enableBackupInput(false);
    voiceButton.disabled = true;
    setCallMode("complete");
  }
}

function setCallMode(mode) {
  orb.className = `voice-orb ${mode}`;
  if (mode === "connecting") {
    callHint.textContent = ui().callConnecting;
    setStatus(ui().connecting, "active");
  } else if (mode === "listening") {
    callHint.textContent = ui().callLive;
    setStatus(ui().listening, "active");
  } else if (mode === "speaking") {
    callHint.textContent = ui().callLive;
    setStatus(ui().speaking, "active");
  } else if (mode === "processing") {
    callHint.textContent = ui().callLive;
    setStatus(ui().processing, "active");
  } else if (mode === "complete") {
    callHint.textContent = ui().complete;
    setStatus(ui().complete, "active");
  } else if (mode === "urgent") {
    callHint.textContent = ui().urgentFlag;
    setStatus(ui().urgentFlag, "danger");
  } else if (mode === "error") {
    callHint.textContent = ui().realtimeUnavailable;
    setStatus(ui().error, "warning");
  } else if (mode === "ended") {
    callHint.textContent = ui().callEnded;
    setStatus(ui().ready, "idle");
  } else {
    callHint.textContent = ui().callReady;
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
  startButton.textContent = sessionId ? text.restart : text.start;
  voiceButton.textContent = text.end;
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
    resetConversationUi();
    setCallMode("ready");
  } else if (lastState) {
    updateState(lastState);
  }
}

applyLanguage();
