import { STATUS, ago, formatDuration, tripSummary } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { Sparkline } from './Sparkline';

export function TruckDetail() {
  const { selectedTruck: truck } = useDashboard();
  const trip = truck ? tripSummary(truck.path) : null;

  return (
    <div className="card" style={{ padding: 14 }}>
      <div className="detail" id="detail">
        {!truck ? (
          <div className="noSel">
            Elegí un camión en el mapa o en la lista para ver su detalle.
          </div>
        ) : (
          <>
            <div className="when">
              <span>
                <b style={{ color: 'var(--ink)', fontSize: '14px' }}>{truck.plate}</b>
                {' · '}
                <span
                  style={{
                    color: truck.active ? STATUS[truck.status].color : 'var(--muted)',
                    fontWeight: '600',
                  }}
                >
                  {truck.active ? STATUS[truck.status].label : 'Inactivo'}
                </span>
              </span>
              <span>{truck.updated ? ago(truck.updated) : 'Sin señal'}</span>
            </div>

            <div className="st">
              <div>
                <b>{truck.speed}</b>
                <span>km/h</span>
              </div>
              <div>
                <b>{truck.fuel != null ? `${truck.fuel}%` : '—'}</b>
                <span>Combustible</span>
              </div>
              <div>
                <b>{Math.round(truck.heading)}°</b>
                <span>Rumbo</span>
              </div>
            </div>

            <dl className="info">
              <dt>Chofer</dt>
              <dd>{truck.driver || '—'}</dd>
              <dt>Ruta</dt>
              <dd>{truck.route || '—'}</dd>
              <dt>Posición</dt>
              <dd>
                {truck.lat != null && truck.lng != null
                  ? `${truck.lat.toFixed(3)}, ${truck.lng.toFixed(3)}`
                  : '—'}
              </dd>
            </dl>

            <div className="trip">
              <div className="trip-h">Recorrido reciente</div>
              {trip ? (
                <div className="trip-st">
                  <div>
                    <b>{trip.km.toFixed(1)}</b>
                    <span>km</span>
                  </div>
                  <div>
                    <b>{formatDuration(trip.minutes)}</b>
                    <span>Duración</span>
                  </div>
                  <div>
                    <b>{trip.points}</b>
                    <span>Puntos</span>
                  </div>
                </div>
              ) : (
                <p className="trip-none">
                  {truck.active
                    ? 'Sin recorrido suficiente todavía.'
                    : 'Camión inactivo: no recibe nuevas posiciones.'}
                </p>
              )}
            </div>

            {truck.history.length > 1 && <Sparkline data={truck.history} />}
          </>
        )}
      </div>
    </div>
  );
}
