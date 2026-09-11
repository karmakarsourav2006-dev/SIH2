/* Shared Supabase authentication guard for the existing static frontend. */
(function () {
  const PUBLIC_PAGES = new Set(['login.html', 'login']);
  const page = window.location.pathname.split('/').pop() || 'login.html';
  const isPublic = PUBLIC_PAGES.has(page);
  const apiBase = window.location.port === '3000'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin;

  let clientPromise;
  let client;

  async function getClient() {
    if (!clientPromise) {
      clientPromise = fetch(`${apiBase}/api/public-config`, { credentials: 'omit' })
        .then(response => response.ok ? response.json() : Promise.reject(new Error('Configuration unavailable')))
        .then(config => {
          if (!config.supabaseUrl || !config.supabaseAnonKey || !window.supabase?.createClient) {
            throw new Error('Supabase is not configured');
          }
          client = window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey, {
            auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
          });
          return client;
        });
    }
    return clientPromise;
  }

  function friendlyError(error) {
    const message = String(error?.message || '').toLowerCase();
    if (message.includes('invalid login credentials')) return 'Invalid email or password.';
    if (message.includes('email not confirmed')) return 'Please confirm your email before signing in.';
    if (message.includes('already registered')) return 'An account with this email already exists.';
    if (message.includes('password')) return 'Password must be at least 6 characters.';
    if (message.includes('email')) return 'Please enter a valid email address.';
    return 'Unable to complete that request. Please try again.';
  }

  function redirectToLogin() {
    const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    window.location.replace(`login.html?next=${encodeURIComponent(next)}`);
  }

  function addLogoutControl(supabaseClient) {
    const status = document.querySelector('.nav-status');
    if (!status || document.getElementById('polarLogout')) return;
    const button = document.createElement('button');
    button.id = 'polarLogout';
    button.type = 'button';
    button.className = 'btn auth-logout';
    button.textContent = 'Sign out';
    button.addEventListener('click', async () => {
      button.disabled = true;
      const { error } = await supabaseClient.auth.signOut();
      if (error) button.disabled = false;
      else window.location.replace('login.html');
    });
    status.appendChild(button);
  }

  async function protectPage() {
    try {
      const supabaseClient = await getClient();
      const { data: { session } } = await supabaseClient.auth.getSession();
      if (!session) return redirectToLogin();
      addLogoutControl(supabaseClient);
      supabaseClient.auth.onAuthStateChange((_event, nextSession) => {
        if (!nextSession) redirectToLogin();
      });
      document.documentElement.classList.add('auth-ready');
    } catch (error) {
      console.error('[Auth]', error);
      if (!isPublic) redirectToLogin();
      else document.documentElement.classList.add('auth-config-error');
    }
  }

  async function initLogin() {
    if (!isPublic) return protectPage();
    const form = document.getElementById('loginForm');
    if (!form) return;
    const email = document.getElementById('loginEmail');
    const password = document.getElementById('loginPassword');
    const submit = document.getElementById('loginSubmit');
    const message = document.getElementById('authMessage');
    const modeTitle = document.getElementById('authModeTitle');
    const modeCopy = document.getElementById('authModeCopy');
    const modeToggle = document.getElementById('authModeToggle');
    let signUpMode = false;

    function showMessage(text, type) {
      message.textContent = text;
      message.className = `auth-message ${type || ''}`;
      message.hidden = !text;
    }

    modeToggle.addEventListener('click', () => {
      signUpMode = !signUpMode;
      modeTitle.textContent = signUpMode ? 'Create your access' : 'Welcome back';
      modeCopy.textContent = signUpMode ? 'Create an operator account for the Polar Energy AI control room.' : 'Sign in to continue to mission operations.';
      submit.textContent = signUpMode ? 'Create account' : 'Sign in';
      modeToggle.textContent = signUpMode ? 'I already have an account' : 'Create an account';
      showMessage('', '');
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      showMessage('', '');
      if (!email.value.trim()) return showMessage('Please enter your email address.', 'error');
      if (!password.value) return showMessage('Please enter your password.', 'error');
      submit.disabled = true;
      submit.setAttribute('aria-busy', 'true');
      submit.textContent = signUpMode ? 'Creating account…' : 'Signing in…';
      try {
        const supabaseClient = await getClient();
        const result = signUpMode
          ? await supabaseClient.auth.signUp({ email: email.value.trim(), password: password.value })
          : await supabaseClient.auth.signInWithPassword({ email: email.value.trim(), password: password.value });
        if (result.error) throw result.error;
        if (signUpMode && !result.data.session) {
          showMessage('Account created. Check your email to confirm access, then sign in.', 'success');
        } else {
          const next = new URLSearchParams(window.location.search).get('next');
          window.location.replace(next && next.endsWith('.html') ? next : 'index.html');
        }
      } catch (error) {
        showMessage(friendlyError(error), 'error');
      } finally {
        submit.disabled = false;
        submit.removeAttribute('aria-busy');
        submit.textContent = signUpMode ? 'Create account' : 'Sign in';
      }
    });
  }

  window.PolarAuth = { getClient, friendlyError, redirectToLogin };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initLogin, { once: true });
  else initLogin();
})();
