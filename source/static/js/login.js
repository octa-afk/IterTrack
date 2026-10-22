const REDIRECT = '/map'; // página a la que va después de iniciar sesión
const TOKEN_KEY = 'itertrack_token'; // misma clave que usa map.html para el guard de sesión

const $ = s => document.querySelector(s);
function setErr(input, msg){
  const box = input.closest('.f').querySelector('.err');
  box.textContent = msg || '';
  input.setAttribute('aria-invalid', msg ? 'true' : 'false');
  return !msg;
}
document.querySelectorAll('.show').forEach(b => b.addEventListener('click', () => {
  const inp = b.parentElement.querySelector('input');
  const hide = inp.type === 'password';
  inp.type = hide ? 'text' : 'password';
  b.textContent = hide ? 'Ocultar' : 'Mostrar';
  b.setAttribute('aria-label', hide ? 'Ocultar contraseña' : 'Mostrar contraseña');
}));
function setStatus(msg, kind){ const s = $('#status'); s.textContent = msg; s.className = 'status ' + (kind||''); }

// Flujo real: OAuth2 Password Flow contra POST /auth/login (x-www-form-urlencoded).
// El token se guarda en localStorage.itertrack_token y se redirige a /map.
async function sendToServer(username, password){
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({username, password})
  });
  if (!res.ok){
    // La API responde {detail: ...}; nunca innerHTML, solo textContent (vía setStatus)
    let detail = '';
    try{
      const data = await res.json();
      detail = data && data.detail ? String(data.detail) : '';
    }catch(_){}
    throw new Error(detail || 'No pudimos iniciar sesión. Probá de nuevo.');
  }
  const data = await res.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data;
}

const username = $('#username'), pass = $('#pass');
username.addEventListener('blur', () => setErr(username, !username.value.trim() ? 'Ingresá tu usuario.' : ''));
$('#login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const a = setErr(username, !username.value.trim() ? 'Ingresá tu usuario.' : '');
  const b = setErr(pass, !pass.value ? 'Ingresá tu contraseña.' : '');
  if (!a || !b){ (a ? pass : username).focus(); return; }
  const btn = $('#submit'); btn.disabled = true; btn.textContent = 'Ingresando…'; setStatus('');
  try{
    await sendToServer(username.value.trim(), pass.value);
    setStatus('Sesión iniciada. Redirigiendo…','ok');
    setTimeout(() => location.href = REDIRECT, 600);
  }catch(err){
    setStatus(err.message || 'No pudimos iniciar sesión. Probá de nuevo.','bad');
    btn.disabled = false; btn.textContent = 'Iniciar sesión';
  }
});
