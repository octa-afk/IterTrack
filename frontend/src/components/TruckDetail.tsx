import { STATUS, ago } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { Sparkline } from './Sparkline';

export function TruckDetail() {
  const { selectedTruck: truck } = useDashboard();

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
                <span style={{ color: STATUS[truck.status].color, fontWeight: '600' }}>
                  {STATUS[truck.status].label}
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

            {truck.history.length > 1 && <Sparkline data={truck.history} />}
          </>
        )}
      </div>
    </div>
  );
}
