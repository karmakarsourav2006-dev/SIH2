/* Resolve before styles paint; keep this independent of station/application state. */
(() => {
  'use strict';
  const root = document.documentElement;
  const valid = value => value === 'polar-night' ? value : 'arctic-day';
  function restore() {
    try { root.dataset.theme = valid(localStorage.getItem('polar_theme')); }
    catch (_) { root.dataset.theme ||= 'arctic-day'; }
    syncButton();
  }
  function syncButton() {
    const button = document.getElementById('polarThemeToggle');
    if (!button) return;
    const night = root.dataset.theme === 'polar-night';
    button.setAttribute('aria-pressed', String(night));
    button.setAttribute('aria-label', `Switch to ${night ? 'Arctic Day' : 'Polar Night'}`);
    button.title = night ? 'Switch to Arctic Day' : 'Switch to Polar Night';
  }
  restore();
  document.addEventListener('DOMContentLoaded', () => {
    syncButton();
    document.getElementById('polarThemeToggle')?.addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'polar-night' ? 'arctic-day' : 'polar-night';
      try { localStorage.setItem('polar_theme', root.dataset.theme); } catch (_) {}
      syncButton();
    });
  });
  window.addEventListener('pageshow', restore);
  window.addEventListener('storage', event => {
    if (event.key === 'polar_theme' || event.key === null) restore();
  });
})();
