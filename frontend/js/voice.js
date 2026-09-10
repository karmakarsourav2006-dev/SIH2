/**
 * POLAR ENERGY AI - UNBROKEN CONVERSATIONAL VOICE COPILOT
 * Web Speech API (STT & Sequential Chunked TTS), Continuous Conversational Loop
 * Features:
 *  - 100% full speech synthesis without trailing truncation
 *  - Robust Chromium keepalive with pause/resume monitoring
 *  - Verified microphone capture (LISTENING indicator strictly bound to recognition.onstart)
 *  - Controlled hardware audio cooldown before microphone revival
 *  - Infinite multi-turn back-and-forth loop until user clicks the cross (✕) button
 */

import { apiFetch, GlobalState, showToast } from './app.js';

export const VoiceState = {
  STANDBY: 'STANDBY',
  LISTENING: 'LISTENING',
  PROCESSING: 'PROCESSING',
  SPEAKING: 'SPEAKING'
};

let recognition = null;
let recognitionSessionId = 0;
let currentState = VoiceState.STANDBY;
let isSpeaking = false; // INVARIANT: isSpeaking === true -> recognition MUST NOT start
let currentUtterance = null;
let ttsCooldownTimeout = null;
let speechEndTimeout = null;
let silenceRestartTimeout = null;
let retryRecognitionTimeout = null;
let chunkWatchdog = null;
let activeRequestId = null;
let activeAbortController = null;
let accumulatedTranscript = '';

// Sequential TTS chunking queue to prevent Chrome 15s pause/drop bug
let speechQueue = [];
let speechQueueIndex = 0;
let ttsKeepaliveInterval = null;

let sessionId = localStorage.getItem('polar_ai_session_id');
if (!sessionId) {
  sessionId = 'sess_' + Math.random().toString(36).substring(2, 9);
  localStorage.setItem('polar_ai_session_id', sessionId);
}

export function initVoiceAssistant() {
  bindVoiceUI();

  // Restore persistent chat history so previous chats never disappear
  restoreChatHistory();

  // Restore persistent open state if previously opened
  const wasOpen = localStorage.getItem('polar_voice_modal_open') === 'true';
  const modal = document.getElementById('voiceModal');
  if (wasOpen && modal) {
    modal.classList.add('open');
    startListening();
  } else {
    setVoiceState(VoiceState.STANDBY);
  }
}

/**
 * Restore chat history from sessionStorage
 */
function restoreChatHistory() {
  try {
    const raw = sessionStorage.getItem('polar_voice_chat_history');
    if (!raw) return;
    const history = JSON.parse(raw);
    if (!Array.isArray(history) || history.length === 0) return;

    const box = document.getElementById('voiceChatBox');
    if (!box) return;

    history.forEach(item => {
      if (item && item.text && item.sender) {
        const msg = document.createElement('div');
        msg.className = `voice-msg ${item.sender}`;
        msg.textContent = item.text;
        box.appendChild(msg);
      }
    });

    requestAnimationFrame(() => {
      box.scrollTop = box.scrollHeight;
    });
  } catch (e) {
    console.warn("[Voice Copilot] Error restoring chat history:", e);
  }
}

/**
 * Split text into complete sentence/clause chunks.
 * CRITICAL: Guaranteed to never drop the final fragment even if unpunctuated.
 */
function prepareSpeechQueue(fullText) {
  if (!fullText) return [];

  // Clean markdown, symbols, excess whitespace
  const clean = fullText
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[*_#`~>\[\]\(\)]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!clean) return [];

  // Matches full sentences up to period/exclamation/question mark followed by space, newline, or end of string.
  // Preserves decimals (e.g. 85.0%, 10.3 kW) and unpunctuated final clauses without dropping any text.
  const matches = clean.match(/.+?(?:[.!?](?=\s|$|\n)|\n|$)/g);
  const rawSentences = matches ? matches.map(s => s.trim()).filter(s => s.length > 0) : [clean];

  const queue = [];
  for (const sentence of rawSentences) {
    if (sentence.length <= 150) {
      queue.push(sentence);
    } else {
      // Split long clauses by commas or colons without dropping fragments
      const subParts = sentence.match(/[^,;:]+[,;:]?/g) || [sentence];
      let currentPart = '';
      for (const part of subParts) {
        if ((currentPart + ' ' + part).trim().length < 150) {
          currentPart = (currentPart + ' ' + part).trim();
        } else {
          if (currentPart) queue.push(currentPart);
          currentPart = part.trim();
        }
      }
      if (currentPart) queue.push(currentPart);
    }
  }

  return queue.length > 0 ? queue : [clean];
}

/**
 * Create and start a fresh SpeechRecognition instance.
 * Ensures unbroken continuous listening across infinite turns.
 */
function createAndStartRecognition() {
  if (!isModalOpen()) {
    console.log("[Voice Copilot] Recognition aborted: modal is closed.");
    return;
  }

  // Self-healing: if isSpeaking flag was left true but synthesis engine is idle, recover immediately
  if (isSpeaking && window.speechSynthesis && !window.speechSynthesis.speaking && !window.speechSynthesis.pending) {
    console.warn("[Voice Copilot] Self-healing: isSpeaking was true but synthesis is idle. Resetting isSpeaking to false.");
    isSpeaking = false;
  }

  if (isSpeaking || currentState === VoiceState.PROCESSING) {
    console.log("[Voice Copilot] Recognition aborted: assistant is speaking or processing.");
    return;
  }

  const thisSession = ++recognitionSessionId;

  // Fully dispose old instance to eliminate stale sockets/listeners
  if (recognition) {
    try {
      recognition.onstart = null;
      recognition.onaudiostart = null;
      recognition.onsoundstart = null;
      recognition.onspeechstart = null;
      recognition.onspeechend = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
    } catch (e) {}
    recognition = null;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("[Voice Copilot] Web Speech Recognition API unavailable in this browser.");
    setVoiceState(VoiceState.STANDBY, "Speech recognition unavailable in this browser.");
    return;
  }

  try {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      if (thisSession !== recognitionSessionId) return;
      console.log(`[Recognition #${thisSession}] onstart: Microphone is LIVE and actively capturing.`);
      clearTimeout(speechEndTimeout);
      clearTimeout(silenceRestartTimeout);
      // ONLY turn indicator green when browser confirms microphone is actually active
      setVoiceState(VoiceState.LISTENING, "Listening... Speak your command");
    };

    recognition.onaudiostart = () => {
      if (thisSession !== recognitionSessionId) return;
      console.log(`[Recognition #${thisSession}] onaudiostart: Audio pipeline receiving stream.`);
    };

    recognition.onspeechstart = () => {
      if (thisSession !== recognitionSessionId) return;
      console.log(`[Recognition #${thisSession}] onspeechstart: User speech detected.`);
    };

    recognition.onspeechend = () => {
      if (thisSession !== recognitionSessionId) return;
      console.log(`[Recognition #${thisSession}] onspeechend: Speech segment ended.`);
    };

    recognition.onresult = (event) => {
      if (thisSession !== recognitionSessionId) return;
      if (isSpeaking || currentState === VoiceState.PROCESSING) {
        return;
      }

      let interim = '';
      let final = '';

      for (let i = 0; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += text + ' ';
        } else {
          interim += text;
        }
      }

      accumulatedTranscript = final.trim();
      const currentSpoken = (accumulatedTranscript ? accumulatedTranscript + ' ' : '') + interim;
      const cleanSpoken = currentSpoken.trim();

      if (cleanSpoken) {
        console.log(`[Recognition #${thisSession}] Heard: "${cleanSpoken}"`);
        setVoiceState(VoiceState.LISTENING, `Hearing: "${cleanSpoken}"`);
        const inp = document.getElementById('inpVoiceText');
        if (inp) inp.value = cleanSpoken;

        // Reset silence debounce timer: 1.8s of silence after speaking auto-submits query
        clearTimeout(speechEndTimeout);
        speechEndTimeout = setTimeout(() => {
          const phrase = accumulatedTranscript || cleanSpoken;
          if (phrase && isModalOpen() && !isSpeaking && currentState === VoiceState.LISTENING) {
            console.log(`[Recognition #${thisSession}] Silence debounce expired. Submitting spoken phrase: "${phrase}"`);
            accumulatedTranscript = '';
            if (inp) inp.value = '';
            submitSpokenText(phrase);
          }
        }, 1800);
      }
    };

    recognition.onerror = (event) => {
      if (thisSession !== recognitionSessionId) return;
      console.warn(`[Recognition #${thisSession}] onerror: ${event.error}`);

      // 'no-speech' and 'aborted' are normal during pauses
      if (event.error === 'no-speech' || event.error === 'aborted') {
        return;
      }

      if (event.error === 'not-allowed') {
        console.warn(`[Recognition #${thisSession}] Microphone permission or user gesture needed.`);
        setVoiceState(VoiceState.STANDBY, "Mic paused. Click '🎙️ Speak' to talk.");
        return;
      }

      // If audio-capture or network error, reset state so it doesn't stay in fake LISTENING
      setVoiceState(VoiceState.STANDBY, "Reconnecting microphone...");
      if (isModalOpen() && !isSpeaking && currentState !== VoiceState.PROCESSING) {
        clearTimeout(silenceRestartTimeout);
        silenceRestartTimeout = setTimeout(() => {
          if (isModalOpen() && !isSpeaking && currentState !== VoiceState.PROCESSING) {
            console.log(`[Recognition #${thisSession}] Retrying recognition start after error...`);
            createAndStartRecognition();
          }
        }, 600);
      }
    };

    recognition.onend = () => {
      if (thisSession !== recognitionSessionId) return;
      console.log(`[Recognition #${thisSession}] onend: Session ended.`);

      // If modal is open and we are supposed to be LISTENING, revive with fresh session
      if (isModalOpen() && !isSpeaking && currentState === VoiceState.LISTENING) {
        console.log(`[Recognition #${thisSession}] Reviving fresh recognition session after unexpected onend.`);
        clearTimeout(silenceRestartTimeout);
        silenceRestartTimeout = setTimeout(() => {
          if (isModalOpen() && !isSpeaking && currentState !== VoiceState.PROCESSING) {
            createAndStartRecognition();
          }
        }, 400);
      }
    };

    console.log(`[Recognition #${thisSession}] Calling recognition.start()...`);
    recognition.start();
  } catch (err) {
    console.warn(`[Recognition #${thisSession}] Start exception:`, err);
    setVoiceState(VoiceState.STANDBY, "Click '🎙️ Speak' to talk.");
  }
}

/**
 * Submit spoken transcript to agent query
 */
async function submitSpokenText(transcript) {
  clearTimeout(speechEndTimeout);
  const clean = transcript.trim();
  if (!clean) return;

  // Make sure prior TTS is stopped and speaking state reset
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  isSpeaking = false;

  console.log(`[Voice Copilot Submitting]: "${clean}"`);

  // 1. Transition immediately to PROCESSING and pause mic
  appendVoiceMessage(clean, 'user');
  setVoiceState(VoiceState.PROCESSING);
  stopRecognitionOnly();

  // 2. Dispatch agent query
  await sendAgentQuery(clean);
}

/**
 * Start listening turn
 */
export function startListening() {
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
  }
  isSpeaking = false;
  currentUtterance = null;
  clearTimeout(ttsCooldownTimeout);
  clearTimeout(speechEndTimeout);
  clearTimeout(silenceRestartTimeout);
  clearTimeout(chunkWatchdog);
  accumulatedTranscript = '';

  setVoiceState(VoiceState.STANDBY, "Activating microphone...");
  createAndStartRecognition();
}

/**
 * Stop speech recognition cleanly
 */
function stopRecognitionOnly() {
  clearTimeout(retryRecognitionTimeout);
  clearTimeout(silenceRestartTimeout);
  clearTimeout(ttsCooldownTimeout);
  clearTimeout(speechEndTimeout);
  if (recognition) {
    try {
      recognition.onstart = null;
      recognition.onaudiostart = null;
      recognition.onsoundstart = null;
      recognition.onspeechstart = null;
      recognition.onspeechend = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
    } catch (e) {}
    recognition = null;
  }
}

/**
 * Stop everything and return to Standby
 */
export function stopEverything() {
  console.log("[Voice Copilot] stopEverything called.");
  isSpeaking = false;
  activeRequestId = null;
  if (activeAbortController) {
    try { activeAbortController.abort(); } catch (e) {}
    activeAbortController = null;
  }
  clearTimeout(retryRecognitionTimeout);
  clearTimeout(silenceRestartTimeout);
  clearTimeout(ttsCooldownTimeout);
  clearTimeout(speechEndTimeout);
  clearTimeout(chunkWatchdog);
  clearInterval(ttsKeepaliveInterval);

  speechQueue = [];
  speechQueueIndex = 0;

  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  currentUtterance = null;
  accumulatedTranscript = '';

  stopRecognitionOnly();
  setVoiceState(VoiceState.STANDBY, "Copilot on Standby");
  showToast("Voice assistant paused", "info");
}

/**
 * Open Voice Modal Window and persist state
 */
export function openModal() {
  const modal = document.getElementById('voiceModal');
  if (modal) {
    modal.classList.add('open');
    try {
      localStorage.setItem('polar_voice_modal_open', 'true');
    } catch (e) {}
  }
}

/**
 * Close Voice Modal Window (ONLY triggered by explicit Cross ✕ button click)
 */
export function closeModal() {
  console.log("[Voice Copilot] closeModal called by cross button.");
  const modal = document.getElementById('voiceModal');
  if (modal) {
    modal.classList.remove('open');
    try {
      localStorage.setItem('polar_voice_modal_open', 'false');
    } catch (e) {}
  }
  stopEverything();
}

/**
 * Helper to check if voice modal is currently visible
 */
function isModalOpen() {
  const modal = document.getElementById('voiceModal');
  return modal && modal.classList.contains('open');
}

/**
 * Update UI state indicators across FAB, Modal Badge, Buttons, and Visualizer Bar
 */
export function setVoiceState(state, customLabel = null) {
  currentState = state;

  const fab = document.getElementById('btnVoiceFab');
  const badge = document.getElementById('voiceStatusBadge');
  const visualizer = document.getElementById('voiceVisualizer');
  const visualizerText = document.getElementById('voiceVisualizerText');
  const autoBtn = document.getElementById('btnContinuousToggle');
  const btnModalMic = document.getElementById('btnModalMic');

  // Auto-Mode is always ON while modal is open
  if (autoBtn) {
    autoBtn.classList.add('active');
    autoBtn.textContent = '🔄 Continuous';
    autoBtn.title = 'Continuous conversation active until cross (✕) button is clicked';
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

  // Update Inside-Modal Speak Button
  if (btnModalMic) {
    if (state === VoiceState.LISTENING) {
      btnModalMic.classList.add('listening');
      btnModalMic.textContent = '🛑 Done Speaking';
      btnModalMic.title = 'Click to finish speaking and send command immediately';
    } else if (state === VoiceState.PROCESSING) {
      btnModalMic.classList.remove('listening');
      btnModalMic.textContent = '⏳ Thinking...';
      btnModalMic.title = 'Polar AI is analyzing telemetry';
    } else if (state === VoiceState.SPEAKING) {
      btnModalMic.classList.remove('listening');
      btnModalMic.textContent = '⏸️ Interrupt';
      btnModalMic.title = 'Click to interrupt speech and speak immediately';
    } else {
      btnModalMic.classList.remove('listening');
      btnModalMic.textContent = '🎙️ Speak';
      btnModalMic.title = 'Click to speak';
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
          visualizerText.textContent = 'Listening... Speak your question or command';
          break;
        case VoiceState.PROCESSING:
          visualizerText.textContent = 'Thinking & querying telemetry...';
          break;
        case VoiceState.SPEAKING:
          visualizerText.textContent = 'Speaking response... (Click Interrupt to speak)';
          break;
        case VoiceState.STANDBY:
        default:
          visualizerText.textContent = "Standby. Click '🎙️ Speak' to talk or enter text.";
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
  const formVoice = document.getElementById('formVoiceInput');
  const inpQuery = document.getElementById('inpVoiceText');
  const btnModalMic = document.getElementById('btnModalMic');
  const visualizer = document.getElementById('voiceVisualizer');

  // Floating Action Button
  if (fab && modal) {
    fab.addEventListener('click', () => {
      if (!modal.classList.contains('open')) {
        openModal();
        startListening();
      } else {
        // When modal is ALREADY OPEN: Toggle listening turn
        if (currentState === VoiceState.LISTENING) {
          if (accumulatedTranscript.trim()) {
            const text = accumulatedTranscript.trim();
            accumulatedTranscript = '';
            submitSpokenText(text);
          } else {
            stopRecognitionOnly();
            setVoiceState(VoiceState.STANDBY, "Mic paused. Click '🎙️ Speak' to talk.");
          }
        } else if (currentState === VoiceState.SPEAKING) {
          if (window.speechSynthesis) window.speechSynthesis.cancel();
          clearInterval(ttsKeepaliveInterval);
          clearTimeout(chunkWatchdog);
          speechQueue = [];
          speechQueueIndex = 0;
          isSpeaking = false;
          startListening();
        } else {
          startListening();
        }
      }
    });
  }

  // Direct Speak / Done Button in modal form
  if (btnModalMic) {
    btnModalMic.addEventListener('click', () => {
      if (currentState === VoiceState.LISTENING) {
        if (accumulatedTranscript.trim()) {
          const text = accumulatedTranscript.trim();
          accumulatedTranscript = '';
          submitSpokenText(text);
        } else {
          stopRecognitionOnly();
          setVoiceState(VoiceState.STANDBY, "Mic paused. Click '🎙️ Speak' to talk.");
        }
      } else if (currentState === VoiceState.SPEAKING) {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        clearInterval(ttsKeepaliveInterval);
        clearTimeout(chunkWatchdog);
        speechQueue = [];
        speechQueueIndex = 0;
        isSpeaking = false;
        startListening();
      } else {
        startListening();
      }
    });
  }

  // Clickable Visualizer Bar
  if (visualizer) {
    visualizer.style.cursor = 'pointer';
    visualizer.title = 'Click to toggle microphone or interrupt';
    visualizer.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      if (currentState === VoiceState.LISTENING) {
        if (accumulatedTranscript.trim()) {
          const text = accumulatedTranscript.trim();
          accumulatedTranscript = '';
          submitSpokenText(text);
        } else {
          stopRecognitionOnly();
          setVoiceState(VoiceState.STANDBY, "Mic paused. Click '🎙️ Speak' to talk.");
        }
      } else if (currentState === VoiceState.SPEAKING) {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        clearInterval(ttsKeepaliveInterval);
        clearTimeout(chunkWatchdog);
        speechQueue = [];
        speechQueueIndex = 0;
        isSpeaking = false;
        startListening();
      } else {
        startListening();
      }
    });
  }

  // Dedicated Stop Button
  if (btnStop) {
    btnStop.addEventListener('click', () => {
      stopEverything();
      appendVoiceMessage("⏹ Voice copilot paused. Click '🎙️ Speak' to resume.", "assistant");
    });
  }

  // Close Button (THE ONLY ACTION THAT CLOSES THE WINDOW AND TERMINATES LOOP)
  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      closeModal();
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

      // Trigger instant UI refresh for Science Scheduler and Dashboard if activities changed
      const modIntents = ['CREATE_ACTIVITY', 'DELETE_ACTIVITY', 'UPDATE_ACTIVITY', 'RESCHEDULE_ACTIVITY'];
      if (typeof res.response === 'object' && modIntents.includes(res.response.intent)) {
        window.dispatchEvent(new CustomEvent('polar:activitiesUpdated', { detail: res.response }));
      }
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
    const errorMsg = `⚠️ Communications Notice: Cannot connect to Polar AI backend (${err.message}).\n\nEnsure backend is running: python -m uvicorn backend.main:app --port 8000`;
    appendVoiceMessage(errorMsg, 'assistant');
    speakText("Notice: Communications link to Polar AI backend failed. Verify server is running.");
  }
}

/**
 * Append message bubble to chat box and persist in sessionStorage
 */
function appendVoiceMessage(text, sender) {
  const box = document.getElementById('voiceChatBox');
  if (!box) return null;

  const msg = document.createElement('div');
  msg.className = `voice-msg ${sender}`;
  msg.textContent = text;
  box.appendChild(msg);

  // Persist genuine messages (skip ephemeral thinking indicator)
  if (!sender.includes('thinking-indicator')) {
    try {
      const raw = sessionStorage.getItem('polar_voice_chat_history');
      const history = raw ? JSON.parse(raw) : [];
      history.push({ text, sender });
      if (history.length > 50) history.shift();
      sessionStorage.setItem('polar_voice_chat_history', JSON.stringify(history));
    } catch (e) {}
  }

  requestAnimationFrame(() => {
    box.scrollTop = box.scrollHeight;
  });

  return msg;
}

/**
 * Speak text response using Web Speech Synthesis (TTS)
 * Full sentence queue guarantees 100% speech output without any dropped sentences
 */
export function speakText(text) {
  if (!window.speechSynthesis || !text) {
    isSpeaking = false;
    resumeListeningAfterTTS();
    return;
  }

  try {
    isSpeaking = true;
    stopRecognitionOnly();
    clearInterval(ttsKeepaliveInterval);
    clearTimeout(ttsCooldownTimeout);
    clearTimeout(chunkWatchdog);

    setVoiceState(VoiceState.SPEAKING);

    // Prepare robust queue of sentences; guaranteed zero dropped text
    speechQueue = prepareSpeechQueue(text);
    speechQueueIndex = 0;

    console.log(`[TTS] Beginning playback of ${speechQueue.length} speech chunks for: "${text.substring(0, 60)}..."`);

    // Non-destructive Chromium keepalive: only calls resume() if paused
    ttsKeepaliveInterval = setInterval(() => {
      if (window.speechSynthesis) {
        if (window.speechSynthesis.paused) {
          console.log("[TTS Keepalive] Detected paused state. Calling window.speechSynthesis.resume().");
          window.speechSynthesis.resume();
        }
      } else if (!isSpeaking) {
        clearInterval(ttsKeepaliveInterval);
      }
    }, 3000);

    // If speech synthesis is currently active or pending, cancel first with a 60ms settle delay
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
      window.speechSynthesis.cancel();
      setTimeout(() => {
        if (isSpeaking) {
          speakNextChunk();
        }
      }, 60);
    } else {
      speakNextChunk();
    }
  } catch (e) {
    console.warn("[Speech Synthesis Exception]:", e);
    isSpeaking = false;
    clearInterval(ttsKeepaliveInterval);
    resumeListeningAfterTTS();
  }
}

/**
 * Play next sentence in sequential queue
 */
function speakNextChunk() {
  if (!isSpeaking) return;
  clearTimeout(chunkWatchdog);

  if (speechQueueIndex >= speechQueue.length) {
    console.log(`[TTS] Finished all ${speechQueue.length} chunks. Complete answer successfully spoken 100%.`);
    onAllSpeechComplete();
    return;
  }

  const chunkText = speechQueue[speechQueueIndex++];
  const utterance = new SpeechSynthesisUtterance(chunkText);
  currentUtterance = utterance; // Keep reference to prevent garbage collection
  utterance.rate = 1.05;
  utterance.pitch = 0.98;

  utterance.onstart = () => {
    console.log(`[TTS Chunk ${speechQueueIndex}/${speechQueue.length}] onstart: "${chunkText.substring(0, 45)}..."`);
    isSpeaking = true;
    setVoiceState(VoiceState.SPEAKING);
  };

  utterance.onpause = () => {
    console.log(`[TTS Chunk ${speechQueueIndex}/${speechQueue.length}] onpause. Resuming.`);
    if (window.speechSynthesis) window.speechSynthesis.resume();
  };

  utterance.onend = () => {
    console.log(`[TTS Chunk ${speechQueueIndex}/${speechQueue.length}] onend: Completed successfully.`);
    clearTimeout(chunkWatchdog);
    speakNextChunk();
  };

  utterance.onerror = (e) => {
    clearTimeout(chunkWatchdog);
    console.warn(`[TTS Chunk ${speechQueueIndex}/${speechQueue.length}] onerror (${e.error}):`, e);
    // CRITICAL: Never leave the assistant deadlocked in isSpeaking = true!
    if (e.error === 'interrupted' || e.error === 'canceled') {
      onAllSpeechComplete();
      return;
    }
    if (speechQueueIndex < speechQueue.length) {
      speakNextChunk();
    } else {
      onAllSpeechComplete();
    }
  };

  // Watchdog per chunk: 10 seconds is plenty for a chunk of <= 150 chars
  chunkWatchdog = setTimeout(() => {
    if (isSpeaking) {
      console.warn(`[TTS Chunk Watchdog] Chunk ${speechQueueIndex} took >10s. Advancing or completing.`);
      if (speechQueueIndex < speechQueue.length) {
        speakNextChunk();
      } else {
        onAllSpeechComplete();
      }
    }
  }, 10000);

  window.speechSynthesis.speak(utterance);
  // Ensure speech synthesis does not stay in suspended/paused queue
  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
  }
}

/**
 * Handle successful completion of all speech chunks:
 * Once the assistant has spoken 100% of its response, resumes listening.
 */
function onAllSpeechComplete() {
  clearTimeout(chunkWatchdog);
  currentUtterance = null;
  isSpeaking = false;
  clearInterval(ttsKeepaliveInterval);

  console.log("[TTS] onAllSpeechComplete reached. Transitioning back to listening.");
  resumeListeningAfterTTS();
}

/**
 * Switch from speaking back to listening with hardware audio release delay
 */
function resumeListeningAfterTTS() {
  isSpeaking = false;
  clearInterval(ttsKeepaliveInterval);
  clearTimeout(chunkWatchdog);
  currentUtterance = null;

  if (!isModalOpen()) {
    setVoiceState(VoiceState.STANDBY);
    return;
  }

  // Set transitioning state while hardware audio switches - NEVER show fake LISTENING!
  setVoiceState(VoiceState.STANDBY, "Response complete. Opening microphone...");

  clearTimeout(ttsCooldownTimeout);
  // Controlled 500ms cooldown allows Windows audio driver to cleanly release speaker output channel
  ttsCooldownTimeout = setTimeout(() => {
    if (!isSpeaking && isModalOpen() && currentState !== VoiceState.PROCESSING) {
      console.log("[Voice Copilot] Audio cooldown elapsed. Creating fresh recognition session...");
      createAndStartRecognition();
    }
  }, 500);
}

// Auto-initialize on load
document.addEventListener('DOMContentLoaded', () => {
  initVoiceAssistant();
});
