/**
 * BOREAS AI Microgrid - Operational Advisor & Voice Terminal
 */

const API_BASE = window.location.origin.startsWith('http') ? window.location.origin : 'http://127.0.0.1:8000';

const inputQuery = document.getElementById('inputAiQuery');
const btnSubmit = document.getElementById('btnSubmitQuery');
const quickChips = document.querySelectorAll('.btn-chip');
const outputBox = document.getElementById('advisorOutput');
const triageTag = document.getElementById('triageTag');
const explanationText = document.getElementById('advisorExplanation');
const actionsList = document.getElementById('advisorActionsList');
const btnVoiceSpeak = document.getElementById('btnVoiceSpeak');

let latestVoiceScript = "";

export function initAssistant() {
  if (btnSubmit && inputQuery) {
    btnSubmit.addEventListener('click', () => {
      const q = inputQuery.value.trim();
      if (q) submitQuery(q);
    });

    inputQuery.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = inputQuery.value.trim();
        if (q) submitQuery(q);
      }
    });
  }

  // Quick preset chips
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (inputQuery) inputQuery.value = prompt;
      submitQuery(prompt);
    });
  });

  // Voice speech synthesis
  if (btnVoiceSpeak) {
    btnVoiceSpeak.addEventListener('click', () => {
      if ('speechSynthesis' in window && latestVoiceScript) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(latestVoiceScript);
        utterance.rate = 1.0;
        utterance.pitch = 0.95;
        window.speechSynthesis.speak(utterance);
      } else {
        alert("Audio Voice Readout: " + (latestVoiceScript || "No transmission loaded."));
      }
    });
  }
}

async function submitQuery(queryText) {
  if (!outputBox) return;

  try {
    if (btnSubmit) btnSubmit.textContent = "Analyzing...";
    const res = await fetch(`${API_BASE}/api/assistant/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderAdvisorResponse(data);
  } catch (err) {
    console.error('Assistant query error:', err);
  } finally {
    if (btnSubmit) btnSubmit.textContent = "Transmit to AI";
  }
}

function renderAdvisorResponse(data) {
  if (!outputBox) return;
  outputBox.style.display = 'flex';

  // Triage Tag
  const isEmerg = String(data.triage_priority).includes('CRITICAL') || String(data.triage_priority).includes('EMERGENCY');
  triageTag.className = `triage-tag ${isEmerg ? 'emergency' : 'advisory'}`;
  triageTag.textContent = `${data.category} // ${data.triage_priority}`;

  // Explanation
  explanationText.textContent = data.explanation;

  // Actions
  actionsList.innerHTML = '';
  if (data.actions_taken && data.actions_taken.length > 0) {
    data.actions_taken.forEach(act => {
      const li = document.createElement('li');
      li.textContent = act;
      actionsList.appendChild(li);
    });
  }

  // Voice Script
  latestVoiceScript = data.voice_script || data.explanation;
  if (btnVoiceSpeak) {
    btnVoiceSpeak.style.display = 'inline-flex';
  }
}

