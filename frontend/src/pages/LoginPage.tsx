import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Mark';
import { ApiError, setToken } from '../api/client';
import { login } from '../api/auth';
import { getConfig } from '../api/config';

const LIVE_ROWS = [
  { dot: '#a6e3c4', plate: 'AF 412 KD', speed: '82 km/h', route: 'Córdoba → Rosario' },
  { dot: '#f6cf7a', plate: 'AG 233 MP', speed: 'Detenido', route: 'Córdoba → Tucumán' },
  { dot: '#ffa49a', plate: 'AF 678 NC', speed: '105 km/h', route: 'Río Cuarto → San Luis' },
];

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'No pudimos iniciar sesión. Probá de nuevo.';
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [usernameError, setUsernameError] = useState('');
  const [passError, setPassError] = useState('');
  const [status, setStatus] = useState<{ text: string; kind: '' | 'ok' | 'bad' }>({
    text: '',
    kind: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [demo, setDemo] = useState<{ username: string; password: string } | null>(null);

  // La demo se decide en el servidor: la misma imagen corre para un cliente
  // real con el boton apagado. Si /config falla, la pagina sigue siendo un
  // login normal.
  useEffect(() => {
    let active = true;
    getConfig()
      .then((cfg) => {
        if (!active) return;
        const { enabled, username, password } = cfg.demo;
        if (enabled && username && password) setDemo({ username, password });
      })
      .catch(() => {
        /* sin configuracion no hay boton, pero el login funciona igual */
      });
    return () => {
      active = false;
    };
  }, []);

  const usernameRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);

  const validateUsername = (v: string) => (v.trim() ? '' : 'Ingresá tu usuario.');
  const validatePass = (v: string) => (v ? '' : 'Ingresá tu contraseña.');

  const handleDemo = async () => {
    if (!demo) return;
    setSubmitting(true);
    setStatus({ text: '', kind: '' });
    try {
      const { access_token } = await login(demo.username, demo.password);
      setToken(access_token);
      navigate('/map');
    } catch (err) {
      setStatus({ text: errorMessage(err), kind: 'bad' });
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const uErr = validateUsername(username);
    const pErr = validatePass(password);
    setUsernameError(uErr);
    setPassError(pErr);
    if (uErr) {
      usernameRef.current?.focus();
      return;
    }
    if (pErr) {
      passRef.current?.focus();
      return;
    }
    setSubmitting(true);
    setStatus({ text: '', kind: '' });
    try {
      const { access_token } = await login(username.trim(), password);
      setToken(access_token);
      navigate('/map');
    } catch (err) {
      setStatus({ text: errorMessage(err), kind: 'bad' });
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <main className="shell">
        <section className="brand" aria-hidden={false}>
          <div className="logo">
            <Mark />
            IterTrack
          </div>
          <h2>Toda tu flota, en un solo mapa.</h2>
          <p>
            Seguí cada camión en tiempo real, filtrá por estado y recibí alertas
            antes de que se conviertan en problemas.
          </p>
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
          <h1>Iniciar sesión</h1>
          <p className="lead">Ingresá con tu cuenta para ver el panel de la flota.</p>
          <form id="login-form" noValidate onSubmit={handleSubmit}>
            <div className="f">
              <label htmlFor="username">Usuario</label>
              <div className="input">
                <input
                  id="username"
                  ref={usernameRef}
                  type="text"
                  autoComplete="username"
                  placeholder="Tu usuario"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onBlur={() => setUsernameError(validateUsername(username))}
                  aria-invalid={usernameError ? 'true' : 'false'}
                />
              </div>
              <div className="err" aria-live="polite">
                {usernameError}
              </div>
            </div>

            <div className="f">
              <label htmlFor="pass">Contraseña</label>
              <div className="input pw">
                <input
                  id="pass"
                  ref={passRef}
                  type={showPass ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Tu contraseña"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setPassError(validatePass(password))}
                  aria-invalid={passError ? 'true' : 'false'}
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
              <div className="err" aria-live="polite">
                {passError}
              </div>
            </div>

            <div className="meta">
              <label className="check">
                <input type="checkbox" id="remember" /> Mantener sesión iniciada
              </label>
              <a href="#">¿Olvidaste tu contraseña?</a>
            </div>

            <button className="btn" id="submit" type="submit" disabled={submitting}>
              {submitting ? 'Ingresando…' : 'Iniciar sesión'}
            </button>
            {demo && (
              <button
                className="btn demo"
                id="demo"
                type="button"
                onClick={handleDemo}
                disabled={submitting}
              >
                Entrar a la demo
              </button>
            )}
            <div className={`status ${status.kind}`} role="status" aria-live="polite">
              {status.text}
            </div>
          </form>
          {demo ? (
            <p className="hint centered">Sin registro: flota de ejemplo con datos simulados.</p>
          ) : (
            <p className="alt">
              ¿Todavía no tenés cuenta? <Link to="/register">Crear cuenta</Link>
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
