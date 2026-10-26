import { useEffect, useRef, useState } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { STATUS, ago } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import type { MobileOutletContext } from './context';
import { Icon } from './icons';

/*
 * Panel móvil: el mapa real queda detrás (lo monta `MobileLayout`) y acá sólo
 * viven los controles flotantes del diseño. El buscador escribe `filters.q`,
 * que ya filtra los marcadores de `MapView` además de la lista de Camiones.
 */
export default function MobileMapPage() {
  const { map, openDrawer } = useOutletContext<MobileOutletContext>();
  const { trucks, visibleTrucks, selectedTruck, selectedId, filters, setFilter, select } =
    useDashboard();
  const navigate = useNavigate();
  /* La vista previa de la flota es una alternancia local: no cambia de ruta. */
  const [flotaAbierta, setFlotaAbierta] = useState(false);

  const camion = selectedTruck ?? trucks[0] ?? null;
  const estado = camion
    ? camion.active
      ? STATUS[camion.status]
      : { label: 'Inactivo', color: 'var(--m-muted)' }
    : null;
  const velocidad =
    camion && camion.active && camion.status !== 'stop' ? camion.speed : '—';

  const verDetalle = (id: number) => {
    select(id);
    navigate(`/fleet?truck=${id}`);
  };

  /*
   * Elegir un camión desde la vista previa lo selecciona y encuadra el mapa en
   * él: si quedaba fuera de la vista, el pin azul aparecía en un lugar que el
   * operador no estaba mirando.
   */
  const elegirCamion = (id: number, lat: number | null, lng: number | null) => {
    select(id);
    setFlotaAbierta(false);
    const instancia = map.current;
    if (!instancia || lat === null || lng === null) return;
    instancia.flyTo([lat, lng], Math.max(instancia.getZoom() || 15, 15), {
      duration: 0.5,
    });
  };

  /*
   * Al entrar al panel el mapa puede venir de estar oculto (`display:none` en
   * otra sección) con el tamaño en cero. Se invalida el tamaño y se encuadra
   * sobre el camión visible: sin esto Leaflet conserva una vista calculada con
   * un contenedor de 0×0.
   */
  const camionRef = useRef(camion);
  useEffect(() => {
    camionRef.current = camion;
  });
  useEffect(() => {
    const mapInstance = map.current;
    if (!mapInstance) return;
    const timer = window.setTimeout(() => {
      mapInstance.invalidateSize();
      const actual = camionRef.current;
      if (actual?.lat != null && actual.lng != null) {
        mapInstance.flyTo(
          [actual.lat, actual.lng],
          Math.max(mapInstance.getZoom() || 13, 13),
          { duration: 0.6 },
        );
      }
    }, 50);
    return () => window.clearTimeout(timer);
  }, [map]);

  return (
    <section className="m-screen m-screen--map">
      <div className="m-searchbar" role="search">
        <button
          className="m-btn-ghost"
          type="button"
          onClick={openDrawer}
          aria-label="Abrir menú"
        >
          <Icon name="menu" />
        </button>
        <label className="m-sr-only" htmlFor="m-q">
          Buscar patente, chofer o ruta
        </label>
        <input
          id="m-q"
          type="search"
          placeholder="Buscar patente, chofer o ruta"
          value={filters.q}
          onChange={(event) => setFilter({ q: event.target.value })}
        />
        <span className="m-searchbar__icon">
          <Icon name="search" size={20} />
        </span>
      </div>

      <div className="m-map-bottom">
        <div className="m-map-controls">
          <button
            className="m-btn-round m-btn-round--locate"
            type="button"
            aria-label="Mi ubicación"
            onClick={() => map.current?.locate({ setView: true, maxZoom: 16 })}
          >
            <Icon name="locate" />
          </button>
        </div>

        <div className={`m-sheet${flotaAbierta ? ' m-sheet--flota' : ''}`}>
          <div className="m-sheet__handle" />
          {camion && estado ? (
            <>
              <button
                className="m-sheet__selected"
                type="button"
                onClick={() => verDetalle(camion.id)}
              >
                <span className="m-dot" style={{ background: estado.color }} />
                <div>
                  <b>{camion.plate}</b>
                  <span className="m-sheet__sub">
                    <span>{estado.label}</span>
                    <span>
                      {camion.updated ? ago(camion.updated) : 'Sin señal'}
                    </span>
                  </span>
                </div>
                <div className="m-sheet__speed">
                  <b>{velocidad}</b>
                  <span>km/h</span>
                </div>
              </button>
              {/*
               * La lista queda montada: el despliegue y el repliegue son la
               * misma transición de altura (0fr ↔ 1fr) más el fundido de la
               * lista, así el botón puede cerrarla con la animación inversa.
               * `inert` la saca del foco y de los toques mientras está plegada.
               */}
              <div
                className={`m-sheet__flota${flotaAbierta ? ' m-sheet__flota--open' : ''}`}
                inert={!flotaAbierta}
              >
                <div className="m-sheet__flota-in">
                  <ul className="m-flota-lista" id="m-flota">
                    {visibleTrucks.map((t) => {
                      const estadoFila = t.active
                        ? STATUS[t.status]
                        : { label: 'Inactivo', color: 'var(--m-muted)' };
                      return (
                        <li key={t.id}>
                          <button
                            className={`m-flota-row${
                              t.id === selectedId ? ' m-flota-row--sel' : ''
                            }`}
                            type="button"
                            onClick={() => elegirCamion(t.id, t.lat, t.lng)}
                          >
                            <span className="m-dot" style={{ background: estadoFila.color }} />
                            <span className="m-flota-row__plate">{t.plate}</span>
                            <span className="m-flota-row__meta">{estadoFila.label}</span>
                            <span className="m-flota-row__speed">
                              <b>{t.active && t.status !== 'stop' ? t.speed : '—'}</b> km/h
                            </span>
                          </button>
                        </li>
                      );
                    })}
                    {!visibleTrucks.length && (
                      <li>
                        <p className="m-sheet__empty">No hay camiones con este filtro.</p>
                      </li>
                    )}
                  </ul>
                </div>
              </div>
              <div className="m-sheet__foot">
                <span>
                  {visibleTrucks.length} de {trucks.length} camiones
                </span>
                <button
                  className="m-btn-dark"
                  type="button"
                  aria-expanded={flotaAbierta}
                  aria-controls="m-flota"
                  onClick={() => setFlotaAbierta((abierta) => !abierta)}
                >
                  {flotaAbierta ? 'Ocultar flota' : 'Ver flota'}
                  <span
                    className="m-sheet__chevron"
                    style={{ transform: `rotate(${flotaAbierta ? 180 : 0}deg)` }}
                  >
                    <Icon name="chevronUp" size={16} stroke={2.2} />
                  </span>
                </button>
              </div>
            </>
          ) : (
            <p className="m-sheet__empty">Todavía no hay camiones en la flota.</p>
          )}
        </div>
      </div>
    </section>
  );
}
