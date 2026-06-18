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

let sessionId = null;
let lastState = null;
let recognition = null;
let recognizing = false;
let autoVoiceEnabled = true;
let assistantSpeaking = false;
let selectedVoice = null;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = navigator.language || "en-US";

  recognition.addEventListener("start", () => {
    recognizing = true;
    voiceButton.classList.add("listening");
    voiceButton.setAttribute("aria-label", "Stop voice input");
    setStatus("Listening", "active");
  });

  recognition.addEventListener("end", () => {
    recognizing = false;
    voiceButton.classList.remove("listening");
    voiceButton.setAttribute("aria-label", "Start voice input");
    if (!lastState?.complete && !assistantSpeaking) {
      setStatus("Ready", "active");
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
    addMessage("system", "Voice input was not available. You can continue by typing.");
    setStatus("Voice unavailable", "warning");
  });
} else {
  voiceButton.disabled = true;
  voiceButton.title = "Voice input is not supported in this browser";
}

startButton.addEventListener("click", async () => {
  await startSession();
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
  setStatus("Starting", "active");
  autoVoiceEnabled = true;
  window.speechSynthesis?.cancel();
  const response = await fetch("/api/start", { method: "POST" });
  const payload = await response.json();
  sessionId = payload.session_id;
  transcriptEl.innerHTML = "";
  startButton.textContent = "Restart Check-in";
  messageInput.disabled = false;
  sendButton.disabled = false;
  voiceButton.disabled = !recognition;
  updateState(payload.state);
  renderAssistantMessages(payload.assistant_messages || []);
  messageInput.focus();
}

async function sendMessage(text) {
  addMessage("user", text);
  setStatus("Processing", "active");
  const response = await fetch("/api/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  const payload = await response.json();
  if (!response.ok) {
    addMessage("system", payload.error || "Something went wrong.");
    setStatus("Error", "warning");
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
      ? "Not captured"
      : `${state.pain.score}/10 (${state.pain.severity})`;
  redFlagValue.textContent = state.safety?.red_flag_present
    ? `Yes: ${state.safety.red_flag_symptoms.join(", ")}`
    : state.safety?.red_flag_uncertain
      ? "Uncertain"
      : "No urgent red flags";
  identityValue.textContent = state.identity?.status || "Not confirmed";

  if (state.report) {
    reportOutput.textContent = state.report;
    saveReportButton.disabled = false;
  } else {
    reportOutput.textContent = "The report will appear here after the check-in is complete.";
    saveReportButton.disabled = true;
  }

  if (state.safety?.red_flag_present) {
    setStatus("Urgent flag", "danger");
  } else if (state.complete) {
    setStatus("Complete", "active");
    sendButton.disabled = true;
    messageInput.disabled = true;
    voiceButton.disabled = true;
  } else {
    setStatus("Ready", "active");
  }
}

function setStatus(text, tone = "idle") {
  statusText.textContent = text;
  statusDot.className = `status-dot ${tone}`;
}

function speakQueue(messages) {
  if (!messages.length) {
    maybeStartAutoListening();
    return;
  }
  const [first, ...rest] = messages;
  speak(first, () => speakQueue(rest));
}

function speak(text, onEnd) {
  if (!("speechSynthesis" in window)) {
    if (onEnd) {
      onEnd();
    } else {
      maybeStartAutoListening();
    }
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
  utterance.onstart = () => {
    assistantSpeaking = true;
    setStatus("Speaking", "active");
  };
  utterance.onend = () => {
    assistantSpeaking = false;
    if (onEnd) {
      onEnd();
    } else {
      maybeStartAutoListening();
    }
  };
  utterance.onerror = () => {
    assistantSpeaking = false;
    if (onEnd) {
      onEnd();
    } else {
      maybeStartAutoListening();
    }
  };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function getPreferredVoice() {
  if (selectedVoice) {
    return selectedVoice;
  }
  if (!("speechSynthesis" in window)) {
    return null;
  }
  const voices = window.speechSynthesis.getVoices();
  const preferredNames = [
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
    voices.find((voice) => /female|woman|samantha|victoria|jenny|aria|karen/i.test(voice.name)) ||
    voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("en")) ||
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
    recognition.start();
  } catch (error) {
    setStatus("Ready", "active");
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
    return "Not started";
  }
  return step
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

addMessage(
  "system",
  "This local prototype supports typed input and browser voice input when available. Start a check-in when ready."
);
