const API = window.location.origin.startsWith('http') ? window.location.origin : 'http://127.0.0.1:8000';
const list = document.getElementById('equipmentSignatureList');
const notified = new Set();

function esc(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function render(rows) {
  if (!list) return;
  list.innerHTML = rows.map(d => {
    const dev = Number(d.deviation_percent || 0);
    const tone = d.status === 'CRITICAL_MALFUNCTION' ? 'critical' : d.status === 'WARNING' ? 'warning' : 'normal';
    return `<div class="equipment-row ${tone}"><div><strong>${esc(d.name)}</strong><small>${esc(d.subsystem)} · ${esc(d.priority_tier)}</small></div><div class="equipment-reading">Expected: ${Number(d.nominal_kw).toFixed(1)} kW | Live: ${Number(d.observed_kw).toFixed(1)} kW (${dev >= 0 ? '+' : ''}${dev.toFixed(1)}%)</div><span class="equipment-status ${tone}">${esc(d.status)}</span><button class="btn-polar" data-device="${esc(d.device_id)}">Inspect</button><button class="btn-polar isolate" data-device="${esc(d.device_id)}">Isolate</button></div>`;
  }).join('');
  list.querySelectorAll('.isolate').forEach(b => b.onclick = () => equipmentAction(b.dataset.device, 'ISOLATE'));
  list.querySelectorAll('.equipment-row button:not(.isolate)').forEach(b => b.onclick = () => alert(rows.find(r => r.device_id === b.dataset.device)?.diagnosis || 'No active diagnosis.'));
}
async function refresh() { try { const r = await fetch(`${API}/api/equipment/signatures`); const rows = await r.json(); render(rows); rows.filter(d => d.flagged && !notified.has(d.device_id)).forEach(d => { notified.add(d.device_id); if (typeof window.showToast === 'function') window.showToast(`${d.name}: ${d.status}`, 'error'); }); } catch (e) { console.warn('Equipment monitor unavailable', e); } }
async function equipmentAction(device_id, action) { await fetch(`${API}/api/equipment/${device_id}/action`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})}); refresh(); }
window.simulateMalfunction = async (device_id = 'EQ-FREEZER-01', observed_kw = 3.4) => { const r = await fetch(`${API}/api/equipment/evaluate`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({device_id, observed_kw})}); const data = await r.json(); refresh(); return data; };
refresh(); setInterval(refresh, 10000);
