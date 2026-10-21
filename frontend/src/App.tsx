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
  const selectedTruck = trucks.find(truck => truck.id === selected)
  return <div className="dashboard"><div ref={mapElement} className="map" /><aside className="sidebar"><strong className="brand-mark">IterTrack</strong><nav><a className="active">⌂ <span>Panel</span></a><a>▱ <span>Camiones</span></a><a>⌘ <span>Rutas</span></a><a>⌁ <span>Reportes</span></a><a>⚙ <span>Ajustes</span></a></nav><button className="logout" onClick={logout}>⇥ &nbsp; Salir</button></aside><header className="topbar"><button className="nav-toggle">☰</button><input aria-label="Buscar camiones" placeholder="Buscar patente, chofer o ruta" value={query} onChange={event => setQuery(event.target.value)} /><span className="alert-count">{trucks.filter(truck => truck.status === 'alert').length} alertas</span><span className="avatar">OC</span></header><section className="map-title"><h1>Mapa en vivo</h1><span>Actualizando</span></section><aside className="fleet-panel"><div className="fleet-tabs"><button className="active">Toda la flota</button><button>Solo alertas</button></div><div className="filter-chips"><span className="active">Todos</span><span>En movimiento</span><span>Detenidos</span><span>Apagados</span></div><div className="fleet-heading"><h2>Flota</h2><small>{visible.length} de {trucks.length} camiones</small></div>{error && <p className="error">{error}</p>}<ul>{visible.map(truck => <li key={truck.id} className={truck.id === selected ? 'selected' : ''}><button onClick={() => { setSelected(truck.id); if (truck.lat !== undefined && truck.long !== undefined) mapRef.current?.flyTo([truck.lat, truck.long], 12) }}><i /><span>{truck.plate}</span><b>{truck.speed.toFixed(0)} <small>km/h</small></b><small>{truck.status === 'alert' ? 'Alerta' : 'hace 1 s'}</small></button></li>)}</ul></aside>{selectedTruck && <section className="detail-card"><h3>{selectedTruck.plate} <em>{selectedTruck.status === 'alert' ? '· Alerta' : ''}</em></h3><div className="stats"><b>{selectedTruck.speed.toFixed(0)}<small>km/h</small></b><b>—<small>Combustible</small></b><b>{Math.round(selectedTruck.heading)}°<small>Rumbo</small></b></div><dl><dt>Chofer</dt><dd>—</dd><dt>Ruta</dt><dd>—</dd><dt>Posición</dt><dd>{selectedTruck.lat?.toFixed(3)}, {selectedTruck.long?.toFixed(3)}</dd></dl></section>}<section className="bottom-card speed-card"><h3>Velocidad por camión <span>Ahora</span></h3><div className="speed-bars">{visible.map(truck => <i key={truck.id} style={{ height: `${Math.max(8, Math.min(100, truck.speed))}%` }}><small>{truck.plate.slice(-3)}</small></i>)}</div></section><section className="bottom-card summary-card"><h3>Resumen de flota</h3><div><b>{trucks.filter(truck => truck.status === 'move' || truck.status === 'alert').length}<small>En ruta</small></b><b>—<small>Combustible</small></b><b>{trucks.length}<small>Con señal</small></b></div></section></div>
}

export function App() { if (window.location.pathname === '/register') return <Register />; if (window.location.pathname === '/map') return <MapDashboard />; return <Login /> }
