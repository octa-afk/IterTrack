import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BrandLogo } from '../components/BrandLogo';
import { ApiError, setToken } from '../api/client';
import { login } from '../api/auth';
import { getConfig } from '../api/config';

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'No pudimos iniciar sesión. Probá de nuevo.';
}

function DemoIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20.5 3.5L13.8 20.5L11.2 12.8L3.5 10.2Z" />
    </svg>
  );
}

function EyeIcon({ off }: { off: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="3" />
      {off && <path d="M4 4l16 16" />}
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [usernameError, setUsernameError] = useState('');
  const [passError, setPassError] = useState('');
  const [status, setStatus] = useState('');
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
    setStatus('');
    try {
      const { access_token } = await login(demo.username, demo.password);
      setToken(access_token);
      navigate('/map');
    } catch (err) {
      setStatus(errorMessage(err));
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
    setStatus('');
    try {
      const { access_token } = await login(username.trim(), password);
      setToken(access_token);
      navigate('/map');
    } catch (err) {
      setStatus(errorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <header className="lg-header">
        <BrandLogo />
      </header>

      <main className="lg-main">
        <h1 className="lg-title">
          Toda tu flota,
          <br />
          en un solo <strong>mapa</strong>
        </h1>

        <form className="lg-card" noValidate onSubmit={handleSubmit}>
          <p className="lg-intro">Ingresá para ver el panel de tu flota</p>

          {demo && (
            <>
              <button
                className="lg-btn lg-btn-demo"
                type="button"
                onClick={handleDemo}
                disabled={submitting}
              >
                <DemoIcon />
                Entrar a la demo
              </button>
              <p className="lg-or">o</p>
            </>
          )}

          <div>
            <input
              id="username"
              className="lg-input"
              ref={usernameRef}
              type="text"
              autoComplete="username"
              aria-label="Usuario"
              placeholder="Usuario"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onBlur={() => setUsernameError(validateUsername(username))}
              aria-invalid={usernameError ? 'true' : 'false'}
              aria-describedby="username-error"
            />
            <div id="username-error" className="lg-error" aria-live="polite">
              {usernameError}
            </div>
          </div>

          <div>
            <div className="lg-password">
              <input
                id="pass"
                className="lg-input"
                ref={passRef}
                type={showPass ? 'text' : 'password'}
                autoComplete="current-password"
                aria-label="Contraseña"
                placeholder="Contraseña"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => setPassError(validatePass(password))}
                aria-invalid={passError ? 'true' : 'false'}
                aria-describedby="pass-error"
              />
              <button
                className="lg-show"
                type="button"
                aria-label={showPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                onClick={() => setShowPass((v) => !v)}
              >
                <EyeIcon off={showPass} />
              </button>
            </div>
            <div id="pass-error" className="lg-error" aria-live="polite">
              {passError}
            </div>
          </div>

          <button className="lg-btn lg-btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'Ingresando…' : 'Iniciar sesión'}
          </button>
          <div className="lg-status" role="status" aria-live="polite">
            {status}
          </div>

          <p className="lg-note">
            {demo && (
              <>
                La demo usa una flota de ejemplo con datos simulados.
                <br />
              </>
            )}
            ¿Tenés una invitación? <Link to="/register">Registrarme</Link>
          </p>
        </form>
      </main>
    </div>
  );
}
