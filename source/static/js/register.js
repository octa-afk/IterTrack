const REDIRECT = '/map'; // página a la que va después de registrarse e iniciar sesión
const TOKEN_KEY = 'itertrack_token'; // misma clave que usa map.html para el guard de sesión

const $ = s => document.querySelector(s);
const emailOk = v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
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

// Flujo real: POST /auth/register (JSON) + auto-login OAuth2 contra POST /auth/login
// (x-www-form-urlencoded). El token se guarda en localStorage.itertrack_token y
// se redirige a /map. Nunca innerHTML: todos los mensajes van por textContent.
async function sendToServer(payload){
  let res;
  try{
    res = await fetch('/auth/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
  }catch(_){
    throw new Error('No se pudo conectar con el servidor.');
  }
  if (!res.ok){
    // La API responde {detail: ...}
    let detail = '';
    try{
      const data = await res.json();
      detail = data && data.detail ? String(data.detail) : '';
    }catch(_){}
    throw new Error(detail || 'No se pudo crear la cuenta. Intenta de nuevo más tarde.');
  }
  // Registro creado: ingreso automático con las mismas credenciales
  let loginRes;
  try{
    loginRes = await fetch('/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({username: payload.username, password: payload.password})
    });
  }catch(_){
    throw new Error('Cuenta creada, pero no se pudo iniciar sesión. Iniciá sesión manualmente.');
  }
  if (!loginRes.ok){
    throw new Error('Cuenta creada, pero no se pudo iniciar sesión. Iniciá sesión manualmente.');
  }
  const data = await loginRes.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data;
}

const full_name = $('#full_name'), org_name = $('#org_name'), invitation_code = $('#invitation_code');
const email = $('#email'), username = $('#username'), pass = $('#pass'), pass2 = $('#pass2'), terms = $('#terms');
const modeCreateBtn = $('#mode-create'), modeJoinBtn = $('#mode-join');
const orgNameField = $('#org-name-field'), invitationCodeField = $('#invitation-code-field');

// Crear organización (org_name) vs unirse a una existente (invitation_code):
// el backend exige exactamente uno de los dos, así que el campo oculto se
// limpia y se relaja su `required`.
let mode = 'create';
function setMode(next){
  mode = next;
  const isCreate = mode === 'create';
  modeCreateBtn.classList.toggle('active', isCreate);
  modeJoinBtn.classList.toggle('active', !isCreate);
  orgNameField.hidden = !isCreate;
  invitationCodeField.hidden = isCreate;
  org_name.required = isCreate;
  invitation_code.required = !isCreate;
  if (isCreate){ invitation_code.value = ''; } else { org_name.value = ''; }
  setErr(org_name, '');
  setErr(invitation_code, '');
}
modeCreateBtn.addEventListener('click', () => setMode('create'));
modeJoinBtn.addEventListener('click', () => setMode('join'));

const meterColors = ['#e0675c','#eeb04a','#8fb86a','#5fae8a'];
function strength(v){
  let s = 0;
  if (v.length >= 8) s++;
  if (/[a-z]/.test(v) && /[A-Z]/.test(v)) s++;
  if (/\d/.test(v)) s++;
  if (/[^A-Za-z0-9]/.test(v) || v.length >= 12) s++;
  return s;
}
pass.addEventListener('input', () => {
  const s = pass.value ? strength(pass.value) : 0;
  document.querySelectorAll('#meter i').forEach((el,i) => el.style.background = i < s ? meterColors[s-1] : '');
  $('#hint').textContent = !pass.value ? 'Usá al menos 8 caracteres y un número.' : ['Muy débil','Débil','Aceptable','Fuerte'][Math.max(0,s-1)];
});
// El medidor y el hint son solo indicativos: el backend no exige longitud ni
// números, así que no bloquean el envío.
const checks = {
  full_name:        () => setErr(full_name, !full_name.value.trim() ? 'Ingresá tu nombre.' : ''),
  org_name:         () => setErr(org_name, mode === 'create' && !org_name.value.trim() ? 'Ingresá el nombre de tu empresa.' : ''),
  invitation_code:  () => setErr(invitation_code, mode === 'join' && !invitation_code.value.trim() ? 'Ingresá el código de invitación.' : ''),
  email:            () => setErr(email, !email.value.trim() ? 'Ingresá tu correo.' : !emailOk(email.value.trim()) ? 'Revisá el formato del correo.' : ''),
  username:         () => setErr(username, !username.value.trim() ? 'Ingresá tu usuario.' : ''),
  pass:             () => setErr(pass, !pass.value ? 'Ingresá tu contraseña.' : ''),
  pass2:            () => setErr(pass2, pass2.value !== pass.value ? 'Las contraseñas no coinciden.' : !pass2.value ? 'Repetí tu contraseña.' : ''),
  terms:            () => setErr(terms, !terms.checked ? 'Tenés que aceptar los términos para continuar.' : ''),
};
[['full_name',full_name],['org_name',org_name],['invitation_code',invitation_code],['email',email],['username',username],['pass',pass],['pass2',pass2]].forEach(([k,el]) => el.addEventListener('blur', checks[k]));
$('#register-form').addEventListener('submit', async e => {
  e.preventDefault();
  const results = Object.values(checks).map(fn => fn());
  const first = [full_name, org_name, invitation_code, email, username, pass, pass2, terms][results.indexOf(false)];
  if (first){ first.focus(); return; }
  const btn = $('#submit'); btn.disabled = true; btn.textContent = 'Creando cuenta…'; setStatus('');
  const payload = {
    username: username.value.trim(),
    email: email.value.trim(),
    full_name: full_name.value.trim(),
    password: pass.value
  };
  // Exactamente uno de los dos, según el modo activo
  if (mode === 'create'){ payload.org_name = org_name.value.trim(); }
  else { payload.invitation_code = invitation_code.value.trim(); }
  try{
    await sendToServer(payload);
    setStatus('Cuenta creada. Redirigiendo al panel…','ok');
    setTimeout(() => { window.location.href = REDIRECT; }, 600);
  }catch(err){
    setStatus(err.message || 'No se pudo crear la cuenta. Intenta de nuevo más tarde.','bad');
    btn.disabled = false; btn.textContent = 'Crear cuenta';
  }
});
