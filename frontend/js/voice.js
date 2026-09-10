/**
 * POLAR ENERGY AI - VOICE ASSISTANT & TACTICAL COPILOT
 * Web Speech API (STT/TTS), AI Operational Reasoning & Voice Modals
 */

import { apiFetch, GlobalState, showToast } from './app.js';

let recognition = null;
let isListening = false;

export function initVoiceAssistant() {
  setupSpeechRecognition();
  bindVoiceUI();
}

/**
 * Configure Browser Speech Recognition
 */
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.info("Web Speech API recognition not available in this browser. Falling back to text prompt.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    isListening = true;
    const fab = document.getElementById('btnVoiceFab');
    if (fab) fab.classList.add('recording');
    showToast("Voice Copilot listening...", "info");
  };

  recognition.onresult = async (event) => {
    const transcript = event.results[0][0].transcript;
    appendVoiceMessage(transcript, 'user');
    await sendAgentQuery(transcript);
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    stopListening();
  };

  recognition.onend = () => {
    stopListening();
  };
}

function startListening() {
  if (recognition) {
    try {
      recognition.start();
    } catch (e) {
      console.warn("Recognition start error:", e);
    }
  }
}

function stopListening() {
  isListening = false;
  const fab = document.getElementById('btnVoiceFab');
  if (fab) fab.classList.remove('recording');
}

/**
 * Bind Voice Modal & Buttons
 */
function bindVoiceUI() {
  const fab = document.getElementById('btnVoiceFab');
  const modal = document.getElementById('voiceModal');
  const btnClose = document.getElementById('btnCloseVoice');
  const formVoice = document.getElementById('formVoiceInput');
  const inpQuery = document.getElementById('inpVoiceText');

  if (fab && modal) {
    fab.addEventListener('click', () => {
      modal.classList.toggle('open');
      if (modal.classList.contains('open') && recognition && !isListening) {
        startListening();
      }
    });
  }

  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      modal.classList.remove('open');
      stopListening();
    });
  }

  if (formVoice && inpQuery) {
    formVoice.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = inpQuery.value.trim();
      if (!text) return;
      inpQuery.value = '';
      appendVoiceMessage(text, 'user');
      await sendAgentQuery(text);
    });
  }
}

/**
 * Send natural query to backend Ollama / Agent engine
 */
async function sendAgentQuery(query) {
  try {
    const res = await apiFetch('/api/ai_chat', {
      method: 'POST',
      body: JSON.stringify({
        query: query,
        station_id: GlobalState.stationId
      })
    });

    if (res && res.ok && res.response) {
      let displayText = '';
      let spokenText = '';

      if (typeof res.response === 'object') {
        displayText = res.response.explanation || res.response.voice_text || JSON.stringify(res.response);
        spokenText = res.response.voice_text || displayText;
      } else {
        displayText = String(res.response);
        spokenText = displayText;
      }

      appendVoiceMessage(displayText, 'assistant');
      speakText(spokenText);
    }
  } catch (err) {
    appendVoiceMessage("Apologies, tactical comms link with Polar AI engine timed out.", 'assistant');
  }
}

/**
 * Append message bubble to chat box
 */
function appendVoiceMessage(text, sender) {
  const box = document.getElementById('voiceChatBox');
  if (!box) return;

  const msg = document.createElement('div');
  msg.className = `voice-msg ${sender}`;
  msg.textContent = text;
  box.appendChild(msg);
  box.scrollTop = box.scrollHeight;
}

/**
 * Speak text response using Web Speech Synthesis
 */
function speakText(text) {
  if (!window.speechSynthesis) return;

  window.speechSynthesis.cancel(); // Clear queued speech
  const clean = text.replace(/[*_#`]/g, ''); // strip markdown
  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.05;
  utterance.pitch = 0.95;
  window.speechSynthesis.speak(utterance);
}

document.addEventListener('DOMContentLoaded', () => {
  initVoiceAssistant();
});



