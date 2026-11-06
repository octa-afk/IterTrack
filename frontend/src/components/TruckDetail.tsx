import { STATUS, ago, formatDistance, formatMinutes, rumboCardinal } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { useNextStop } from '../state/useNextStop';
import { Sparkline } from './Sparkline';

/*
 * Panel del camión actual. Misma distribución que la referencia: encabezado con
 * patente y estado, una grilla 2x2 de métricas y, a la derecha, lo que falta
 * hasta la próxima parada con el historial de velocidad debajo. Vive sobre el
 * mapa (`.detailcard` lo posiciona en el layout del panel) y también lo reusa la
 * sección Camiones dentro de una columna.
 */
export function TruckDetail() {
  const { selectedTruck: truck } = useDashboard();
  const nextStop = useNextStop(truck?.id ?? null, truck?.lat ?? null, truck?.lng ?? null);
  const estado = truck
    ? truck.active
      ? STATUS[truck.status]
      : { label: 'Inactivo', color: 'var(--muted)' }
    : null;

  return (
    <div className="card detailcard">
      <div className="detail" id="detail">
        {!truck || !estado ? (
          <div className="noSel">
            Elegí un camión en el mapa o en la lista para ver su detalle.
          </div>
        ) : (
          <>
            <div className="dc-h">
              <b>{truck.plate}</b>
              <span style={{ color: estado.color }}>
                {estado.label} · {truck.updated ? ago(truck.updated) : 'Sin señal'}
              </span>
            </div>

            <div className="dc-body">
              <div className="dc-tiles">
                <div className="dc-tile">
                  <span>Velocidad (km/h)</span>
                  <b className="big">
                    {truck.active && truck.status !== 'stop' ? truck.speed : '—'}
                  </b>
                </div>
                <div className="dc-tile">
                  <span>Combustible</span>
                  <b>{truck.fuel != null ? `${truck.fuel}%` : '—'}</b>
                </div>
                <div className="dc-tile">
                  <span>Chofer</span>
                  <b title={truck.driver || undefined}>{truck.driver || '—'}</b>
                </div>
                <div className="dc-tile">
                  <span>Rumbo</span>
                  <b>
                    {truck.updated ? (
                      <>
                        <svg
                          className="dc-rumbo"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                          style={{ transform: `rotate(${truck.heading}deg)` }}
                        >
                          <path d="M12 2.5l7.5 19-7.5-4.4-7.5 4.4z" />
                        </svg>
                        {Math.round(truck.heading)}° {rumboCardinal(truck.heading)}
                      </>
                    ) : (
                      '—'
                    )}
                  </b>
                </div>
              </div>

              <div className="dc-trip">
                <div className="dc-trip-h">
                  Próxima parada
                  {nextStop?.state === 'ok' && <span> · parada {nextStop.stopSeq}</span>}
                </div>
                {nextStop?.state === 'ok' ? (
                  <div className="dc-trip-st">
                    <span>
                      <b>{formatDistance(nextStop.distanceM)}</b>
                    </span>
                    <span>
                      <b>{formatMinutes(nextStop.durationS)}</b>
                    </span>
                  </div>
                ) : (
                  <p className="dc-trip-none">
                    {nextStop?.state === 'no-trip'
                      ? 'Sin viaje abierto'
                      : nextStop?.state === 'no-route'
                        ? 'Sin ruta disponible'
                        : ''}
                  </p>
                )}
                {truck.history.length > 1 && <Sparkline data={truck.history} />}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
