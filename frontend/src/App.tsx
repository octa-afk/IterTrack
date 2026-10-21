import { FormEvent, type ReactNode, useState } from 'react'
import { login, register } from './api'

function Field({ label, name, type = 'text', value, onChange, error }: {
  label: string; name: string; type?: string; value: string;
  onChange: (value: string) => void; error?: string
}) {
  return <label className="field">
    <span>{label}</span>
    <input name={name} type={type} value={value} onChange={event => onChange(event.target.value)} />
    {error && <small>{error}</small>}
  </label>
}

function Shell({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return <main className="shell">
    <section className="brand"><strong>IterTrack</strong><h2>Toda tu flota, en un solo mapa.</h2><p>Seguí cada camión en tiempo real desde un solo lugar.</p></section>
    <section className="panel"><h1>{title}</h1><p className="lead">{lead}</p>{children}</section>
  </main>
}

function Login() {
  const [username, setUsername] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!username.trim() || !password) { setError('Ingresá usuario y contraseña.'); return }
    setBusy(true)
    try { await login(username.trim(), password); window.location.href = '/map' }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'No pudimos iniciar sesión.') }
    finally { setBusy(false) }
  }
  return <Shell title="Iniciar sesión" lead="Ingresá con tu cuenta para ver el panel de la flota.">
    <form onSubmit={submit}>
      <Field label="Usuario" name="username" value={username} onChange={setUsername} />
      <Field label="Contraseña" name="password" type="password" value={password} onChange={setPassword} />
      {error && <p className="error" role="alert">{error}</p>}
      <button disabled={busy}>{busy ? 'Ingresando…' : 'Iniciar sesión'}</button>
    </form>
    <p className="alternate">¿Todavía no tenés cuenta? <a href="/register">Crear cuenta</a></p>
  </Shell>
}

function Register() {
  const [mode, setMode] = useState<'create' | 'join'>('create'); const [values, setValues] = useState({ full_name: '', org_name: '', invitation_code: '', email: '', username: '', password: '', password2: '' });
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const update = (name: keyof typeof values) => (value: string) => setValues(current => ({ ...current, [name]: value }))
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (!values.full_name || !values.email || !values.username || !values.password || values.password !== values.password2 || (mode === 'create' ? !values.org_name : !values.invitation_code)) { setError('Revisá los datos ingresados y repetí la contraseña.'); return }
    setBusy(true)
    const payload = { username: values.username.trim(), email: values.email.trim(), full_name: values.full_name.trim(), password: values.password, ...(mode === 'create' ? { org_name: values.org_name.trim() } : { invitation_code: values.invitation_code.trim() }) }
    try { await register(payload); window.location.href = '/map' }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo crear la cuenta.') }
    finally { setBusy(false) }
  }
  return <Shell title="Crear cuenta" lead="Completá tus datos para empezar a usar el panel.">
    <div className="mode"><button type="button" className={mode === 'create' ? 'active' : ''} onClick={() => setMode('create')}>Crear empresa</button><button type="button" className={mode === 'join' ? 'active' : ''} onClick={() => setMode('join')}>Unirse a empresa</button></div>
    <form onSubmit={submit}>
      <Field label="Nombre completo" name="full_name" value={values.full_name} onChange={update('full_name')} />
      {mode === 'create' ? <Field label="Empresa" name="org_name" value={values.org_name} onChange={update('org_name')} /> : <Field label="Código de invitación" name="invitation_code" value={values.invitation_code} onChange={update('invitation_code')} />}
      <Field label="Correo electrónico" name="email" type="email" value={values.email} onChange={update('email')} />
      <Field label="Usuario" name="username" value={values.username} onChange={update('username')} />
      <Field label="Contraseña" name="password" type="password" value={values.password} onChange={update('password')} />
      <Field label="Repetir contraseña" name="password2" type="password" value={values.password2} onChange={update('password2')} />
      {error && <p className="error" role="alert">{error}</p>}
      <button disabled={busy}>{busy ? 'Creando cuenta…' : 'Crear cuenta'}</button>
    </form>
    <p className="alternate">¿Ya tenés cuenta? <a href="/">Iniciar sesión</a></p>
  </Shell>
}

export function App() { return window.location.pathname === '/register' ? <Register /> : <Login /> }
