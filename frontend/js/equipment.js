const API = (window.location.port === '3000') ? 'http://127.0.0.1:8000' : window.location.origin;
const list = document.getElementById('equipmentSignatureList');
const modal = document.getElementById('equipmentModal');
const modalBody = document.getElementById('equipmentModalBody');
const modalTitle = document.getElementById('equipmentModalTitle');
const notified = new Set();
let currentRows = [];
const timeline = JSON.parse(localStorage.getItem('equipmentTimeline') || '{}');
function addEvent(device, label, detail='') { const e={time:new Date().toLocaleTimeString(),label,detail}; timeline[device]=timeline[device]||[]; timeline[device].push(e); localStorage.setItem('equipmentTimeline', JSON.stringify(timeline)); }

function esc(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function render(rows) {
  if (!list) return;
  currentRows = rows;
  list.innerHTML = rows.map(d => {
    const dev = Number(d.deviation_percent || 0);
    const tone = d.status === 'CRITICAL_MALFUNCTION' ? 'critical' : d.status === 'ISOLATED' ? 'isolated' : d.status !== 'NORMAL' ? 'warning' : 'normal';
    return `<div class="equipment-row ${tone}"><div><strong>${esc(d.name)}</strong><small>${esc(d.subsystem)} · ${esc(d.priority_tier)}</small></div><div class="equipment-reading">Expected: ${Number(d.nominal_kw).toFixed(1)} kW | Live: ${Number(d.observed_kw).toFixed(1)} kW (${dev >= 0 ? '+' : ''}${dev.toFixed(1)}%)</div><span class="equipment-status ${tone}">${esc(d.status)}</span><button class="btn-polar inspect" data-device="${esc(d.device_id)}">Inspect</button><button class="btn-polar isolate" data-device="${esc(d.device_id)}">Isolate</button></div>`;
  }).join('');
  list.querySelectorAll('.isolate').forEach(b => b.onclick = () => equipmentAction(b.dataset.device, 'ISOLATE'));
  list.querySelectorAll('.inspect').forEach(b => b.onclick = () => showDiagnosis(rows.find(r => r.device_id === b.dataset.device)));
}
async function refresh() {
  try {
    const r = await fetch(`${API}/api/equipment/signatures`);
    const rows = await r.json();
    if (!r.ok) throw new Error(rows.detail || 'Equipment monitor unavailable.');
    rows.forEach(d => { if (!timeline[d.device_id]) addEvent(d.device_id, 'Monitoring started'); });
    render(rows);
    rows.filter(d => d.flagged && !notified.has(d.device_id)).forEach(d => { notified.add(d.device_id); if (typeof window.showToast === 'function') window.showToast(`${d.name}: ${d.status}`, 'error'); });
  } catch (e) { console.warn('Equipment monitor unavailable', e); }
}
function openModal(title, body) { modalTitle.textContent = title; modalBody.innerHTML = body; modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); }
function closeModal() { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
function showDiagnosis(d) {
  if (!d) return;
  const statusClass = d.status === 'CRITICAL_MALFUNCTION' ? 'critical' : d.status === 'ISOLATED' ? 'isolated' : '';
  const diagnosis = d.diagnosis || (d.status === 'NORMAL' ? 'No active diagnosis. Equipment is operating within its expected energy signature.' : 'No diagnosis is currently available.');
  const action = d.status === 'CRITICAL_MALFUNCTION' ? 'Inspect immediately and issue an isolation command if the abnormal draw persists.' : d.status === 'ISOLATED' ? 'Load marked as isolated and excluded from active energy-management decisions.' : 'Continue monitoring the equipment signature.';
  const events=(timeline[d.device_id]||[]).slice(-12).reverse().map(e=>`<li><time>${esc(e.time)}</time><span>${esc(e.label)}<small>${esc(e.detail||'')}</small></span></li>`).join('')||'<li><span>No recorded events</span></li>';
  openModal('EQUIPMENT DIAGNOSTIC', `<dl><dt>Equipment</dt><dd>${esc(d.name)}</dd><dt>Device ID</dt><dd>${esc(d.device_id)}</dd><dt>Expected Power</dt><dd>${Number(d.nominal_kw).toFixed(1)} kW</dd><dt>Observed Power</dt><dd>${Number(d.observed_kw).toFixed(1)} kW</dd><dt>Deviation</dt><dd>${Number(d.deviation_percent || 0).toFixed(1)}%</dd><dt>Status</dt><dd class="modal-status ${statusClass}">${esc(d.status)}</dd><dt>Risk</dt><dd>${esc(d.risk || 'LOW')}</dd></dl><section class="energy-impact"><h3>ENERGY IMPACT</h3><div>Expected: ${Number(d.nominal_kw).toFixed(1)} kW</div><div>Observed: ${Number(d.observed_kw).toFixed(1)} kW</div><div>Excess: +${Number(d.excess_kw||0).toFixed(1)} kW</div><div>Estimated extra energy: ${Number(d.extra_energy_1h_kwh||0).toFixed(1)} kWh / 1h · ${Number(d.extra_energy_24h_kwh||0).toFixed(1)} kWh / 24h</div></section><div class="equipment-modal-message"><strong>Diagnosis:</strong><br>${esc(diagnosis)}</div><h3>EQUIPMENT EVENT TIMELINE</h3><ol class="equipment-timeline">${events}</ol><div class="equipment-modal-action"><strong>Recommended Action:</strong><br>${esc(action)}</div><button class="btn-polar" type="button" data-close-equipment-modal>Close</button>`);
}
async function equipmentAction(device_id, action) {
  const previous = currentRows.find(r => r.device_id === device_id);
  try {
    const r = await fetch(`${API}/api/equipment/${device_id}/action`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})});
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'The isolation command failed.');
    addEvent(device_id, 'Isolation command issued'); await refresh();
    if (action === 'ISOLATE') { addEvent(device_id, 'Isolation successful'); const b=data.energy_balance; openModal('EQUIPMENT ISOLATED', `<dl><dt>Equipment</dt><dd>${esc(previous?.name || device_id)}</dd><dt>Current Status</dt><dd class="modal-status isolated">${esc(data.status || 'ISOLATED')}</dd></dl><section class="energy-impact"><h3>ENERGY BALANCE</h3><div>Before Isolation — Station Load: ${b.before_station_load_kw} kW · Affected Equipment: ${b.before_equipment_load_kw} kW</div><div>After Isolation — Station Load: ${b.after_station_load_kw} kW · Affected Equipment: ${b.after_equipment_load_kw} kW</div><div>Load Removed: ${b.load_removed_kw} kW</div></section><div class="equipment-modal-action">Isolation command issued. Load removed from the active energy-management calculation.</div><button class="btn-polar" type="button" data-close-equipment-modal>Close</button>`); }
  } catch (e) {
    if (typeof window.showToast === 'function') window.showToast(e.message, 'error');
    else openModal('ISOLATION ERROR', `<div class="equipment-modal-message">${esc(e.message)}</div><button class="btn-polar" type="button" data-close-equipment-modal>Close</button>`);
  }
}
window.simulateMalfunction = async (device_id = 'EQ-FREEZER-01', observed_kw = 3.4) => {
  const r = await fetch(`${API}/api/equipment/evaluate`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({device_id, observed_kw})});
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || 'Malfunction simulation failed.');
  addEvent(device_id, data.status === 'ANOMALY' ? 'Anomaly detected' : data.status === 'PERSISTENT_ANOMALY' ? 'Persistent anomaly detected' : data.status === 'CRITICAL_MALFUNCTION' ? 'Critical malfunction confirmed' : 'Normal operation', `${data.consecutive_abnormal_readings||0}/${data.persistence_required||3} consecutive abnormal readings`); await refresh();
  return data;
};
document.getElementById('simulateEquipmentMalfunction')?.addEventListener('click', async () => { try { const data = await window.simulateMalfunction(); if (typeof window.showToast === 'function') window.showToast(`${data.name}: ${data.status}`, 'error'); } catch (e) { if (typeof window.showToast === 'function') window.showToast(e.message, 'error'); } });
document.getElementById('equipmentModalClose')?.addEventListener('click', closeModal);
modal?.addEventListener('click', e => { if (e.target === modal || e.target.matches('[data-close-equipment-modal]')) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
refresh();
setInterval(refresh, 10000);
