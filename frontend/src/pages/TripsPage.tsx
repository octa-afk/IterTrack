import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import {
  createTrip,
  listAvailableTrucks,
  listChargers,
  listTrips,
} from '../api/destinations';
import type { Charger, Trip } from '../api/types';
import { useDashboard } from '../state/useDashboard';

/*
 * Rutas: viajes con destinos. El formulario sólo existe para `org_admin`
 * porque crear un viaje es escritura; `member` ve la lista y nada más.
 */
const ESTADOS: Record<string, string> = {
  planned: 'Planificado',
  in_progress: 'En curso',
  done: 'Finalizado',
  cancelled: 'Cancelado',
};

const HORA_LOCAL = (iso: string) =>
  new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

const COLOR_ESTADO: Record<string, string> = {
  planned: 'var(--muted)',
  in_progress: 'var(--green)',
  done: 'var(--green-d)',
  cancelled: 'var(--alert)',
};

function valorLocalPorDefecto(): string {
  const ahora = new Date();
  ahora.setMinutes(0, 0, 0);
  ahora.setHours(ahora.getHours() + 1);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${ahora.getFullYear()}-${pad(ahora.getMonth() + 1)}-${pad(ahora.getDate())}T${pad(
    ahora.getHours(),
  )}:${pad(ahora.getMinutes())}`;
}

export default function TripsPage() {
  const { role, trucks: flota } = useDashboard();
  const puedeEditar = role === 'org_admin' || role === 'platform_admin';

  const [trips, setTrips] = useState<Trip[]>([]);
  const [chargers, setChargers] = useState<Charger[]>([]);
  const [disponibles, setDisponibles] = useState<{ id: number; plate: string }[]>([]);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [enviando, setEnviando] = useState(false);

  const [chargerId, setChargerId] = useState('');
  const [truckId, setTruckId] = useState('');
  const [destino, setDestino] = useState('');
  const [salida, setSalida] = useState(valorLocalPorDefecto);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelado = false;

    async function cargar() {
      try {
        const [viajes, dadores, disponibles] = await Promise.all([
          listTrips(),
          listChargers(),
          puedeEditar ? listAvailableTrucks() : Promise.resolve([]),
        ]);
        if (cancelado) return;
        setTrips(viajes);
        setChargers(dadores);
        setDisponibles(disponibles);
        setError('');
      } catch (fallo) {
        if (cancelado) return;
        setError(
          fallo instanceof ApiError ? fallo.message : 'No se pudieron cargar los viajes',
        );
      }
    }

    void cargar();
    return () => {
      cancelado = true;
    };
  }, [puedeEditar, reloadKey]);

  // El valor por defecto se deriva en render: escribirlo desde el efecto
  // dispara un render en cascada sin necesidad.
  const chargerSeleccionado = chargerId || String(chargers[0]?.id ?? '');
  const truckSeleccionado = truckId || String(disponibles[0]?.id ?? '');

  const enviar = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setAviso('');
    setEnviando(true);
    try {
      const viaje = await createTrip({
        charger_id: Number(chargerSeleccionado),
        truck_id: truckSeleccionado ? Number(truckSeleccionado) : null,
        // `datetime-local` no lleva zona: el ISO la agrega en UTC y el backend
        // la exige, así que "07:30" no se interpreta como UTC por accidente.
        departure_at: new Date(salida).toISOString(),
        stops: [{ address: destino }],
      });
      const pendiente = viaje.stops.some((stop) => stop.needs_review);
      setAviso(
        pendiente
          ? `Viaje #${viaje.id} creado. El destino quedó pendiente de ubicar: resolvelo desde el pin en el mapa.`
          : `Viaje #${viaje.id} creado.`,
      );
      setDestino('');
      setReloadKey((n) => n + 1);
    } catch (fallo) {
      setError(fallo instanceof ApiError ? fallo.message : 'No se pudo crear el viaje');
    } finally {
      setEnviando(false);
    }
  };

  const nombreDador = (id: number) => chargers.find((c) => c.id === id)?.name ?? `#${id}`;
  const patente = (id: number | null) =>
    id === null ? '—' : (flota.find((t) => t.id === id)?.plate ?? `#${id}`);

  return (
    <div className={puedeEditar ? 'section-page' : 'section-page solo'}>
      <div className="card trips-card">
        <div className="card-h">
          <h3>Viajes</h3>
          <span className="tag">{trips.length}</span>
        </div>

        {error && <p className="aviso error">{error}</p>}
        {aviso && <p className="aviso ok">{aviso}</p>}

        <div className="trips-wrap">
          <table className="trips-table">
            <thead>
              <tr>
                <th>Salida</th>
                <th>Dador de carga</th>
                <th>Camión</th>
                <th>Destinos</th>
              </tr>
            </thead>
            <tbody>
              {!trips.length && (
                <tr>
                  <td className="empty" colSpan={4}>
                    {puedeEditar
                      ? 'Todavía no hay viajes. Creá el primero desde el formulario.'
                      : 'Todavía no hay viajes cargados.'}
                  </td>
                </tr>
              )}
              {trips.map((trip) => {
                const pendientes = trip.stops.filter((s) => s.needs_review).length;
                return (
                  <tr key={trip.id}>
                    <td>{HORA_LOCAL(trip.departure_at)}</td>
                    <td className="plate" title={nombreDador(trip.charger_id)}>
                      <span className="estado">
                        <span
                          className="dot"
                          style={{ background: COLOR_ESTADO[trip.status] ?? 'var(--muted)' }}
                          title={ESTADOS[trip.status] ?? trip.status}
                        />
                        {nombreDador(trip.charger_id)}
                      </span>
                    </td>
                    <td>{patente(trip.truck_id)}</td>
                    <td>
                      {trip.stops.length}
                      {pendientes > 0 && (
                        <span className="badge-off">{pendientes} sin ubicar</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {puedeEditar && (
        <div className="card">
          <div className="card-h">
            <h3>Nuevo viaje</h3>
          </div>
          {!chargers.length ? (
            <p className="noSel">
              Primero cargá un dador de carga: un viaje siempre pertenece a uno.
            </p>
          ) : (
            <form className="trip-form" onSubmit={enviar}>
              <label className="field">
                <span>Dador de carga</span>
                <select value={chargerSeleccionado} onChange={(e) => setChargerId(e.target.value)}>
                  {chargers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Camión del depósito</span>
                <select value={truckSeleccionado} onChange={(e) => setTruckId(e.target.value)}>
                  <option value="">Sin asignar</option>
                  {disponibles.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.plate}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Destino</span>
                <input
                  value={destino}
                  onChange={(e) => setDestino(e.target.value)}
                  placeholder="Av. Colón 1234, Córdoba"
                  required
                  minLength={3}
                />
              </label>

              <label className="field">
                <span>Salida</span>
                <input
                  type="datetime-local"
                  value={salida}
                  onChange={(e) => setSalida(e.target.value)}
                  required
                />
              </label>

              <button className="btn-primary" type="submit" disabled={enviando}>
                {enviando ? 'Creando…' : 'Crear viaje'}
              </button>
              <p className="hint">
                Si la dirección no se puede ubicar, el viaje se crea igual y el destino queda
                pendiente de revisión.
              </p>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
