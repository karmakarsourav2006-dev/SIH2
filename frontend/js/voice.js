/**
 * POLAR ENERGY AI - CONTINUOUS CONVERSATIONAL VOICE COPILOT
 * Web Speech API (STT & TTS), Multi-turn Conversational Loop, State Indicators & Interlock
 */

import { apiFetch, GlobalState, showToast } from './app.js';

export const VoiceState = {
  STANDBY: 'STANDBY',
  LISTENING: 'LISTENING',
  PROCESSING: 'PROCESSING',
  SPEAKING: 'SPEAKING'
};

let recognition = null;
let currentState = VoiceState.STANDBY;
let isContinuousMode = true; // Auto-resume conversation by default in voice mode
let isSpeaking = false; // INVARIANT: isSpeaking === true -> recognition MUST NOT start
let retryRecognitionTimeout = null;
let currentUtterance = null;
let silenceRestartTimeout = null;
let ttsCooldownTimeout = null;
let activeRequestId = null;
let activeAbortController = null;

let sessionId = localStorage.getItem('polar_ai_session_id');
if (!sessionId) {
  sessionId = 'sess_' + Math.random().toString(36).substring(2, 9);
  localStorage.setItem('polar_ai_session_id', sessionId);
}

export function initVoiceAssistant() {
  setupSpeechRecognition();
  bindVoiceUI();
  setVoiceState(VoiceState.STANDBY);
}

/**
 * Configure Browser Speech Recognition (STT)
 */
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("[Voice Copilot] Web Speech Recognition API is unavailable in this browser.");
    return;
  }

  try {
    recognition = new SpeechRecognition();
    recognition.continuous = false; // Turn-based segmenting is most reliable with browser TTS handoff
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      clearTimeout(silenceRestartTimeout);
      setVoiceState(VoiceState.LISTENING);
    };

    recognition.onresult = async (event) => {
      // Guard against late recognition firing while assistant is speaking
      if (isSpeaking) {
        console.warn("[Voice Copilot] Ignored STT result while assistant is speaking.");
        return;
      }

      if (!event.results || !event.results[0] || !event.results[0][0]) return;
      const transcript = event.results[0][0].transcript.trim();
      if (!transcript) return;

      console.log(`[Voice Copilot Heard]: "${transcript}"`);

      // 1. Check for verbal stop / exit commands
      if (isStopCommand(transcript)) {
        appendVoiceMessage(transcript, 'user');
        handleVerbalStop();
        return;
      }

      // 2. Transition immediately to PROCESSING and ensure mic stops capturing
      appendVoiceMessage(transcript, 'user');
      setVoiceState(VoiceState.PROCESSING);
      stopRecognitionOnly();

      // 3. Dispatch agent query
      await sendAgentQuery(transcript);
    };

    recognition.onerror = (event) => {
      console.warn("[Voice Recognition Event Error]:", event.error);

      // Gracefully handle no-speech timeout without breaking continuous mode
      if (event.error === 'no-speech') {
        if (!isSpeaking && isContinuousMode && isModalOpen() && currentState === VoiceState.LISTENING) {
          clearTimeout(silenceRestartTimeout);
          silenceRestartTimeout = setTimeout(() => {
            if (!isSpeaking && isContinuousMode && isModalOpen() && currentState === VoiceState.LISTENING) {
              startListening();
            }
          }, 400);
        }
        return;
      }

      if (event.error === 'not-allowed') {
        showToast("Microphone access denied. Please enable mic permissions.", "error");
        stopEverything();
        return;
      }

      // For network or aborted errors, don't crash
      if (event.error === 'aborted') {
        return;
      }
    };

    recognition.onend = () => {
      // INVARIANT: recognition.abort() triggers onend, but if isSpeaking is true, DO NOT restart!
      if (isSpeaking) {
        return;
      }

      // If we are supposed to be LISTENING and continuous mode is active, restart seamlessly
      if (currentState === VoiceState.LISTENING && isContinuousMode && isModalOpen()) {
        clearTimeout(silenceRestartTimeout);
        silenceRestartTimeout = setTimeout(() => {
          if (!isSpeaking && currentState === VoiceState.LISTENING && isContinuousMode && isModalOpen()) {
            startListening();
          }
        }, 300);
      }
    };
  } catch (err) {
    console.error("[Voice Copilot Init Error]:", err);
  }
}

/**
 * Check if the user said a command to terminate the continuous conversation
 */
function isStopCommand(transcript) {
  const normalized = transcript.toLowerCase();
  const stopKeywords = [
    'stop listening',
    'stop assistant',
    'shut down',
    'stand down',
    'goodbye',
    'bye bye',
    'turn off mic',
    'cancel listening',
    'stop talking',
    'exit copilot'
  ];
  if (stopKeywords.some(kw => normalized.includes(kw))) return true;
  if (/^(stop|exit|goodbye|bye|mute|standdown)$/i.test(normalized)) return true;
  return false;
}

/**
 * Handle verbal request to stop
 */
function handleVerbalStop() {
  isContinuousMode = false;
  stopRecognitionOnly();
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  
  const text = "Standing down. Conversational voice copilot switched to standby mode.";
  appendVoiceMessage(text, 'assistant');
  setVoiceState(VoiceState.SPEAKING);

  // Speak the goodbye without auto-relaunching listening
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.05;
  utterance.onend = () => {
    setVoiceState(VoiceState.STANDBY, "Standing Down (Standby)");
  };
  utterance.onerror = () => {
    setVoiceState(VoiceState.STANDBY);
  };
  window.speechSynthesis.speak(utterance);
}

/**
 * Start listening turn
 */
export function startListening() {
  // Invariant check: If currently speaking, recognition MUST NOT start
  if (isSpeaking) {
    console.warn("[Voice Copilot] startListening blocked because isSpeaking === true");
    return;
  }

  // Ensure we do not listen while synthesis is running!
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
  }

  if (!recognition) {
    setupSpeechRecognition();
  }

  if (recognition) {
    clearTimeout(retryRecognitionTimeout);
    clearTimeout(silenceRestartTimeout);
    clearTimeout(ttsCooldownTimeout);
    try {
      recognition.start();
      setVoiceState(VoiceState.LISTENING);
    } catch (e) {
      // If already started (InvalidStateError), keep listening state
      if (e.name === 'InvalidStateError') {
        setVoiceState(VoiceState.LISTENING);
      } else {
        console.warn("[Recognition Start Error]:", e);
      }
    }
  }
}

/**
 * Stop speech recognition without canceling continuous mode
 */
function stopRecognitionOnly() {
  clearTimeout(retryRecognitionTimeout);
  clearTimeout(silenceRestartTimeout);
  clearTimeout(ttsCooldownTimeout);
  if (recognition) {
    try {
      recognition.abort();
    } catch (e) {
      // Ignored
    }
  }
}

/**
 * Stop everything and return to Standby
 */
export function stopEverything() {
  isContinuousMode = false;
  isSpeaking = false;
  activeRequestId = null;
  if (activeAbortController) {
    try { activeAbortController.abort(); } catch (e) {}
    activeAbortController = null;
  }
  clearTimeout(retryRecognitionTimeout);
  clearTimeout(silenceRestartTimeout);
  clearTimeout(ttsCooldownTimeout);

  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  currentUtterance = null;

  stopRecognitionOnly();
  setVoiceState(VoiceState.STANDBY, "Copilot on Standby");
  showToast("Voice assistant switched to Standby", "info");
}

/**
 * Helper to check if voice modal is currently visible
 */
function isModalOpen() {
  const modal = document.getElementById('voiceModal');
  return modal && modal.classList.contains('open');
}

/**
 * Update UI state indicators across FAB, Modal Badge, and Visualizer Bar
 */
export function setVoiceState(state, customLabel = null) {
  currentState = state;

  const fab = document.getElementById('btnVoiceFab');
  const badge = document.getElementById('voiceStatusBadge');
  const visualizer = document.getElementById('voiceVisualizer');
  const visualizerText = document.getElementById('voiceVisualizerText');
  const autoBtn = document.getElementById('btnContinuousToggle');

  // Update Auto-Mode button
  if (autoBtn) {
    if (isContinuousMode) {
      autoBtn.classList.add('active');
      autoBtn.textContent = '🔄 Auto: ON';
      autoBtn.title = 'Continuous conversation active (click to disable)';
    } else {
      autoBtn.classList.remove('active');
      autoBtn.textContent = '⏸️ Auto: OFF';
      autoBtn.title = 'Single-turn mode (click to enable auto-loop)';
    }
  }

  // Update FAB styles
  if (fab) {
    fab.classList.remove('recording', 'processing', 'speaking');
    if (state === VoiceState.LISTENING) fab.classList.add('recording');
    else if (state === VoiceState.PROCESSING) fab.classList.add('processing');
    else if (state === VoiceState.SPEAKING) fab.classList.add('speaking');
  }

  // Update Status Badge
  if (badge) {
    badge.className = 'voice-status-badge ' + state.toLowerCase();
    switch (state) {
      case VoiceState.LISTENING:
        badge.textContent = '🟢 LISTENING';
        break;
      case VoiceState.PROCESSING:
        badge.textContent = '⏳ THINKING';
        break;
      case VoiceState.SPEAKING:
        badge.textContent = '🔊 SPEAKING';
        break;
      case VoiceState.STANDBY:
      default:
        badge.textContent = '⏹ STANDBY';
        break;
    }
  }

  // Update Waveform Visualizer
  if (visualizer) {
    visualizer.className = 'voice-visualizer ' + state.toLowerCase();
  }

  if (visualizerText) {
    if (customLabel) {
      visualizerText.textContent = customLabel;
    } else {
      switch (state) {
        case VoiceState.LISTENING:
          visualizerText.textContent = isContinuousMode
            ? 'Listening... speak now (Auto-loop active)'
            : 'Listening... speak your command';
          break;
        case VoiceState.PROCESSING:
          visualizerText.textContent = 'Thinking & querying telemetry...';
          break;
        case VoiceState.SPEAKING:
          visualizerText.textContent = 'Speaking response (Mic paused)...';
          break;
        case VoiceState.STANDBY:
        default:
          visualizerText.textContent = 'Standby. Click mic to speak or enter text.';
          break;
      }
    }
  }
}

/**
 * Bind UI controls and events
 */
function bindVoiceUI() {
  const fab = document.getElementById('btnVoiceFab');
  const modal = document.getElementById('voiceModal');
  const btnClose = document.getElementById('btnCloseVoice');
  const btnStop = document.getElementById('btnStopVoice');
  const autoBtn = document.getElementById('btnContinuousToggle');
  const formVoice = document.getElementById('formVoiceInput');
  const inpQuery = document.getElementById('inpVoiceText');

  // Floating Action Button
  if (fab && modal) {
    fab.addEventListener('click', () => {
      modal.classList.toggle('open');
      if (modal.classList.contains('open')) {
        isContinuousMode = true;
        startListening();
      } else {
        stopEverything();
      }
    });
  }

  // Dedicated Stop Button
  if (btnStop) {
    btnStop.addEventListener('click', () => {
      stopEverything();
      appendVoiceMessage("⏹ Voice copilot paused and switched to standby.", "assistant");
    });
  }

  // Continuous Mode Toggle Button
  if (autoBtn) {
    autoBtn.addEventListener('click', () => {
      isContinuousMode = !isContinuousMode;
      if (isContinuousMode && isModalOpen() && currentState === VoiceState.STANDBY) {
        startListening();
      } else {
        setVoiceState(currentState);
      }
    });
  }

  // Close Button
  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      modal.classList.remove('open');
      stopEverything();
    });
  }

  // Text Fallback Form
  if (formVoice && inpQuery) {
    formVoice.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = inpQuery.value.trim();
      if (!text) return;
      inpQuery.value = '';

      stopRecognitionOnly();
      appendVoiceMessage(text, 'user');
      setVoiceState(VoiceState.PROCESSING);
      await sendAgentQuery(text);
    });
  }
}

/**
 * Send natural query to backend FastAPI / Ollama engine
 */
async function sendAgentQuery(query) {
  // Cancel any prior pending network query to eliminate async race conditions
  if (activeAbortController) {
    try { activeAbortController.abort(); } catch (e) {}
  }
  activeAbortController = new AbortController();

  const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
  activeRequestId = requestId;

  const thinkingEl = appendVoiceMessage("⏳ Analyzing station telemetry and consulting BOREAS AI...", "assistant thinking-indicator");

  try {
    const res = await apiFetch('/api/ai_chat', {
      method: 'POST',
      body: JSON.stringify({
        query: query,
        station_id: GlobalState.stationId || 'ST-01',
        session_id: sessionId,
        request_id: requestId
      }),
      signal: activeAbortController.signal
    });

    if (thinkingEl && thinkingEl.parentNode) {
      thinkingEl.remove();
    }

    // Discard stale out-of-order responses from prior overlapping queries
    if (!res || (res.request_id && res.request_id !== activeRequestId) || activeRequestId !== requestId) {
      console.warn(`[Voice Copilot] Discarded stale async response (${res?.request_id} !== active ${activeRequestId})`);
      return;
    }

    if (res.ok && res.response) {
      let displayText = '';
      let spokenText = '';

      if (typeof res.response === 'object') {
        displayText = res.response.explanation || res.response.voice_text || JSON.stringify(res.response);
        spokenText = res.response.voice_text || displayText;
        if (res.response.rag_included) {
          displayText += "\n\n📚 [Scientific Literature Retrieved via RAG]";
        }
      } else {
        displayText = String(res.response);
        spokenText = displayText;
      }

      appendVoiceMessage(displayText, 'assistant');
      speakText(spokenText);
    } else {
      appendVoiceMessage("Operational telemetry update complete.", 'assistant');
      speakText("Operational telemetry update complete.");
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log(`[Voice Copilot] Aborted superseded query: "${query}"`);
      return;
    }
    if (thinkingEl && thinkingEl.parentNode) {
      thinkingEl.remove();
    }
    console.error("[Voice Assistant API Error]:", err);
    const errorMsg = `⚠️ Communications Notice: Cannot connect to Polar AI backend (${err.message}).\n\nEnsure backend is running: 'python -m uvicorn backend.main:app --port 8000'`;
    appendVoiceMessage(errorMsg, 'assistant');
    speakText("Notice: Communications link to Polar AI backend failed. Verify server is running.");
  }
}

/**
 * Append message bubble to chat box
 */
function appendVoiceMessage(text, sender) {
  const box = document.getElementById('voiceChatBox');
  if (!box) return null;

  const msg = document.createElement('div');
  msg.className = `voice-msg ${sender}`;
  msg.textContent = text;
  box.appendChild(msg);
  box.scrollTop = box.scrollHeight;
  return msg;
}

/**
 * Speak text response using Web Speech Synthesis (TTS)
 * Strictly pauses Speech Recognition during speech to prevent feedback loop!
 */
export function speakText(text) {
  if (!window.speechSynthesis || !text) {
    isSpeaking = false;
    // If TTS unavailable, resume listening immediately if continuous
    if (isContinuousMode && isModalOpen()) {
      startListening();
    } else {
      setVoiceState(VoiceState.STANDBY);
    }
    return;
  }

  try {
    // 1. Mark system as speaking immediately to lock all STT restarts
    isSpeaking = true;

    // 2. Abort/stop active speech recognition
    stopRecognitionOnly();

    // 3. Cancel any conflicting existing speech
    window.speechSynthesis.cancel();

    setVoiceState(VoiceState.SPEAKING);

    // Clean formatting: strip markdown, URLs, and code blocks
    const clean = text
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[*_#`~>\[\]\(\)]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const utterance = new SpeechSynthesisUtterance(clean);
    currentUtterance = utterance; // Prevent GC bug in Chrome/Edge
    utterance.rate = 1.05;
    utterance.pitch = 0.98;

    utterance.onstart = () => {
      isSpeaking = true;
      setVoiceState(VoiceState.SPEAKING);
    };

    const onSpeechComplete = () => {
      currentUtterance = null;
      isSpeaking = false;

      // Wait ~300 ms before restarting recognition to ensure mic does not capture speaker echo
      clearTimeout(ttsCooldownTimeout);
      ttsCooldownTimeout = setTimeout(() => {
        // Only restart if recognition is still intended to be active
        if (!isSpeaking && isContinuousMode && isModalOpen()) {
          startListening();
        } else if (!isSpeaking) {
          setVoiceState(VoiceState.STANDBY);
        }
      }, 300);
    };

    utterance.onend = () => {
      onSpeechComplete();
    };

    utterance.onerror = (e) => {
      console.warn("[TTS Speech Error]:", e);
      onSpeechComplete();
    };

    // 4. Start TTS
    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.warn("[Speech Synthesis Exception]:", e);
    isSpeaking = false;
    setVoiceState(VoiceState.STANDBY);
  }
}

// Auto-initialize on load
document.addEventListener('DOMContentLoaded', () => {
  initVoiceAssistant();
});
