import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Mark';
import { ApiError, setToken } from '../api/client';
import { login, register } from '../api/auth';

const LIVE_ROWS = [
  { dot: '#a6e3c4', plate: 'AF 412 KD', speed: '82 km/h', route: 'Córdoba → Rosario' },
  { dot: '#f6cf7a', plate: 'AG 233 MP', speed: 'Detenido', route: 'Córdoba → Tucumán' },
  { dot: '#ffa49a', plate: 'AF 678 NC', speed: '105 km/h', route: 'Río Cuarto → San Luis' },
];

const METER_COLORS = ['#e0675c', '#eeb04a', '#8fb86a', '#5fae8a'];
const STRENGTH_LABELS = ['Muy débil', 'Débil', 'Aceptable', 'Fuerte'];
const emailOk = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);

function strength(v: string): number {
  let s = 0;
  if (v.length >= 8) s++;
  if (/[a-z]/.test(v) && /[A-Z]/.test(v)) s++;
  if (/\d/.test(v)) s++;
  if (/[^A-Za-z0-9]/.test(v) || v.length >= 12) s++;
  return s;
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'No se pudo crear la cuenta. Intentá de nuevo más tarde.';
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'create' | 'join'>('create');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [invitationCode, setInvitationCode] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [pass, setPass] = useState('');
  const [pass2, setPass2] = useState('');
  const [terms, setTerms] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [showPass2, setShowPass2] = useState(false);
  const [status, setStatus] = useState<{ text: string; kind: '' | 'ok' | 'bad' }>({
    text: '',
    kind: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});

  const setErr = (field: string, msg: string) => {
    setErrors((prev) => ({ ...prev, [field]: msg }));
  };

  const focus = (id: string) => document.getElementById(id)?.focus();

  const checks: Record<string, () => string> = {
    full_name: () => (fullName.trim() ? '' : 'Ingresá tu nombre.'),
    org_name: () =>
      mode === 'create' && !orgName.trim() ? 'Ingresá el nombre de tu empresa.' : '',
    invitation_code: () =>
      mode === 'join' && !invitationCode.trim() ? 'Ingresá el código de invitación.' : '',
    email: () =>
      !email.trim()
        ? 'Ingresá tu correo.'
        : !emailOk(email.trim())
          ? 'Revisá el formato del correo.'
          : '',
    username: () => (username.trim() ? '' : 'Ingresá tu usuario.'),
    pass: () => (pass ? '' : 'Ingresá tu contraseña.'),
    pass2: () =>
      pass2 !== pass ? 'Las contraseñas no coinciden.' : !pass2 ? 'Repetí tu contraseña.' : '',
    terms: () => (terms ? '' : 'Tenés que aceptar los términos para continuar.'),
  };

  const switchMode = (next: 'create' | 'join') => {
    setMode(next);
    if (next === 'create') setInvitationCode('');
    else setOrgName('');
    setErrors({});
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const order = ['full_name', 'org_name', 'invitation_code', 'email', 'username', 'pass', 'pass2', 'terms'];
    const fieldErrors: Record<string, string> = {};
    for (const key of order) fieldErrors[key] = checks[key]();
    setErrors(fieldErrors);

    const firstBad = order.find((key) => fieldErrors[key]);
    if (firstBad) {
      focus(firstBad);
      return;
    }

    const payload = {
      username: username.trim(),
      email: email.trim(),
      full_name: fullName.trim(),
      password: pass,
      ...(mode === 'create' ? { org_name: orgName.trim() } : { invitation_code: invitationCode.trim() }),
    };

    setSubmitting(true);
    setStatus({ text: '', kind: '' });
    try {
      await register(payload);
      const { access_token } = await login(payload.username, payload.password);
      setToken(access_token);
      navigate('/map');
    } catch (err) {
      setStatus({ text: errorMessage(err), kind: 'bad' });
      setSubmitting(false);
    }
  };

  const s = pass ? strength(pass) : 0;

  return (
    <div className="auth-page">
      <main className="shell">
        <section className="brand" aria-hidden={false}>
          <div className="logo">
            <Mark />
            IterTrack
          </div>
          <h2>Empezá a controlar tu flota hoy.</h2>
          <p>Creá tu cuenta en un minuto y sumá a tus camiones, choferes y rutas en un solo lugar.</p>
          <div className="live" aria-hidden="true">
            <div className="live-h">En ruta ahora</div>
            <ul>
              {LIVE_ROWS.map((row) => (
                <li key={row.plate}>
                  <i style={{ background: row.dot }} />
                  <b>{row.plate}</b>
                  <em>{row.speed}</em>
                  <span>{row.route}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="side">
          <h1>Crear cuenta</h1>
          <p className="lead">Completá tus datos para empezar a usar el panel.</p>
          <form id="register-form" noValidate onSubmit={handleSubmit}>
            <div className="mode" role="group" aria-label="Modo de registro">
              <button
                type="button"
                id="mode-create"
                className={mode === 'create' ? 'active' : undefined}
                onClick={() => switchMode('create')}
              >
                Crear empresa
              </button>
              <button
                type="button"
                id="mode-join"
                className={mode === 'join' ? 'active' : undefined}
                onClick={() => switchMode('join')}
              >
                Unirse a empresa
              </button>
            </div>

            <div className="row2">
              <div className="f">
                <label htmlFor="full_name">Nombre completo</label>
                <div className="input">
                  <input
                    id="full_name"
                    type="text"
                    autoComplete="name"
                    placeholder="Ana Pérez"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    onBlur={() => setErr('full_name', checks.full_name())}
                    aria-invalid={errors.full_name ? 'true' : 'false'}
                  />
                </div>
                <div className="err" aria-live="polite">
                  {errors.full_name}
                </div>
              </div>

              {mode === 'create' ? (
                <div className="f">
                  <label htmlFor="org_name">Empresa</label>
                  <div className="input">
                    <input
                      id="org_name"
                      type="text"
                      autoComplete="organization"
                      placeholder="Transportes del Sur"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      onBlur={() => setErr('org_name', checks.org_name())}
                      aria-invalid={errors.org_name ? 'true' : 'false'}
                    />
                  </div>
                  <div className="err" aria-live="polite">
                    {errors.org_name}
                  </div>
                </div>
              ) : (
                <div className="f">
                  <label htmlFor="invitation_code">Código de invitación</label>
                  <div className="input">
                    <input
                      id="invitation_code"
                      type="text"
                      autoComplete="off"
                      placeholder="Código que te compartió tu empresa"
                      value={invitationCode}
                      onChange={(e) => setInvitationCode(e.target.value)}
                      onBlur={() => setErr('invitation_code', checks.invitation_code())}
                      aria-invalid={errors.invitation_code ? 'true' : 'false'}
                    />
                  </div>
                  <div className="err" aria-live="polite">
                    {errors.invitation_code}
                  </div>
                </div>
              )}
            </div>

            <div className="f">
              <label htmlFor="email">Correo electrónico</label>
              <div className="input">
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="nombre@empresa.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => setErr('email', checks.email())}
                  aria-invalid={errors.email ? 'true' : 'false'}
                />
              </div>
              <div className="err" aria-live="polite">
                {errors.email}
              </div>
            </div>

            <div className="f">
              <label htmlFor="username">Usuario</label>
              <div className="input">
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  placeholder="Tu usuario"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onBlur={() => setErr('username', checks.username())}
                  aria-invalid={errors.username ? 'true' : 'false'}
                />
              </div>
              <div className="err" aria-live="polite">
                {errors.username}
              </div>
            </div>

            <div className="f">
              <label htmlFor="pass">Contraseña</label>
              <div className="input pw">
                <input
                  id="pass"
                  type={showPass ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Mínimo 8 caracteres"
                  aria-describedby="hint"
                  value={pass}
                  onChange={(e) => setPass(e.target.value)}
                  onBlur={() => setErr('pass', checks.pass())}
                  aria-invalid={errors.pass ? 'true' : 'false'}
                />
                <button
                  className="show"
                  type="button"
                  aria-label={showPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  onClick={() => setShowPass((v) => !v)}
                >
                  {showPass ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              <div className="meter" id="meter" aria-hidden="true">
                {[0, 1, 2, 3].map((i) => (
                  <i key={i} style={{ background: i < s ? METER_COLORS[s - 1] : undefined }} />
                ))}
              </div>
              <div className="hint" id="hint">
                {!pass
                  ? 'Usá al menos 8 caracteres y un número.'
                  : STRENGTH_LABELS[Math.max(0, s - 1)]}
              </div>
              <div className="err" aria-live="polite">
                {errors.pass}
              </div>
            </div>

            <div className="f">
              <label htmlFor="pass2">Repetir contraseña</label>
              <div className="input pw">
                <input
                  id="pass2"
                  type={showPass2 ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Repetí tu contraseña"
                  value={pass2}
                  onChange={(e) => setPass2(e.target.value)}
                  onBlur={() => setErr('pass2', checks.pass2())}
                  aria-invalid={errors.pass2 ? 'true' : 'false'}
                />
                <button
                  className="show"
                  type="button"
                  aria-label={showPass2 ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  onClick={() => setShowPass2((v) => !v)}
                >
                  {showPass2 ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              <div className="err" aria-live="polite">
                {errors.pass2}
              </div>
            </div>

            <div className="f">
              <label className="check">
                <input
                  type="checkbox"
                  id="terms"
                  checked={terms}
                  onChange={(e) => setTerms(e.target.checked)}
                />{' '}
                <span>
                  Acepto los <a href="#">términos de uso</a> y la{' '}
                  <a href="#">política de privacidad</a>.
                </span>
              </label>
              <div className="err" aria-live="polite">
                {errors.terms}
              </div>
            </div>

            <button className="btn" id="submit" type="submit" disabled={submitting}>
              {submitting ? 'Creando cuenta…' : 'Crear cuenta'}
            </button>
            <div className={`status ${status.kind}`} role="status" aria-live="polite">
              {status.text}
            </div>
          </form>
          <p className="alt">
            ¿Ya tenés cuenta? <Link to="/">Iniciar sesión</Link>
          </p>
        </section>
      </main>
    </div>
  );
}
