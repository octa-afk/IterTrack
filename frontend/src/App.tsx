import { FormEvent, type ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { login, register, TOKEN_KEY } from './api'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

type Truck = { id: number; plate: string; lat?: number; long?: number; speed: number; heading: number; recorded_at?: string; status: 'move' | 'idle' | 'stop' | 'alert' }
const apiHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}` })

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

function MapDashboard() {
  const mapElement = useRef<HTMLDivElement>(null); const mapRef = useRef<L.Map | undefined>(undefined);
  const [trucks, setTrucks] = useState<Truck[]>([]); const [selected, setSelected] = useState<number>(); const [query, setQuery] = useState(''); const [error, setError] = useState('')
  useEffect(() => {
    if (!mapElement.current) return
    const map = L.map(mapElement.current).setView([-31.9, -64], 7); mapRef.current = map
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(map)
    return () => { map.remove(); mapRef.current = undefined }
  }, [])
  useEffect(() => {
    let active = true
    async function refresh() {
      try {
        const listResponse = await fetch('/trucks', { headers: apiHeaders() })
        if (listResponse.status === 401) { localStorage.removeItem(TOKEN_KEY); window.location.replace('/'); return }
        if (!listResponse.ok) throw new Error('No se pudo cargar la flota.')
        const list = await listResponse.json() as Array<{ id: number; plate: string }>
        const next = await Promise.all(list.map(async truck => {
          const response = await fetch(`/trucks/${truck.id}/location`, { headers: apiHeaders() })
          if (!response.ok) return { ...truck, speed: 0, heading: 0, status: 'stop' as const }
          const point = await response.json() as { lat: number; long: number; speed: number; heading: number; recorded_at?: string }
          const status: Truck['status'] = point.speed > 90 ? 'alert' : point.speed < 3 ? 'idle' : 'move'
          return { ...truck, ...point, status }
        }))
        if (active) setTrucks(next)
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : 'Error de conexión.') }
    }
    refresh(); const timer = window.setInterval(refresh, 3000); return () => { active = false; window.clearInterval(timer) }
  }, [])
  useEffect(() => {
    const map = mapRef.current; if (!map) return
    const markers = new Map<number, L.Marker>()
    trucks.forEach(truck => {
      if (truck.lat === undefined || truck.long === undefined) return
      const safePlate = truck.plate.replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character] ?? character)
      const icon = L.divIcon({ className: 'truck-marker', html: `<span style="--heading:${truck.heading}deg">▲</span><b>${safePlate}</b>`, iconSize: [42, 42], iconAnchor: [21, 21] })
      const marker = markers.get(truck.id) ?? L.marker([truck.lat, truck.long]).addTo(map)
      marker.setLatLng([truck.lat, truck.long]).setIcon(icon).off('click').on('click', () => setSelected(truck.id)); markers.set(truck.id, marker)
    })
    return () => { markers.forEach(marker => marker.remove()) }
  }, [trucks])
  const visible = useMemo(() => trucks.filter(truck => truck.plate.toLowerCase().includes(query.toLowerCase())), [trucks, query])
  function logout() { localStorage.removeItem(TOKEN_KEY); window.location.replace('/') }
  return <div className="dashboard"><header><strong>IterTrack</strong><input aria-label="Buscar camiones" placeholder="Buscar patente" value={query} onChange={event => setQuery(event.target.value)} /><button onClick={logout}>Salir</button></header><main className="dashboard-main"><section className="map-panel"><h1>Mapa en vivo</h1><div ref={mapElement} className="map" /></section><aside className="fleet-panel"><h2>Flota ({visible.length})</h2>{error && <p className="error">{error}</p>}<ul>{visible.map(truck => <li key={truck.id} className={truck.id === selected ? 'selected' : ''}><button onClick={() => { setSelected(truck.id); if (truck.lat !== undefined && truck.long !== undefined) mapRef.current?.flyTo([truck.lat, truck.long], 12) }}><span>{truck.plate}</span><small>{truck.speed} km/h · {truck.status}</small></button></li>)}</ul></aside></main></div>
}

export function App() { if (window.location.pathname === '/register') return <Register />; if (window.location.pathname === '/map') return <MapDashboard />; return <Login /> }
