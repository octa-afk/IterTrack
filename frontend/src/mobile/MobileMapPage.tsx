import { useEffect, useRef } from 'react';
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
  const { trucks, visibleTrucks, selectedTruck, filters, setFilter, select } = useDashboard();
  const navigate = useNavigate();

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

      <div className="m-map-controls">
        <button
          className="m-btn-round"
          type="button"
          aria-label="Mi ubicación"
          onClick={() => map.current?.locate({ setView: true, maxZoom: 16 })}
        >
          <Icon name="locate" />
        </button>
        <div className="m-zoom">
          <button type="button" aria-label="Acercar" onClick={() => map.current?.zoomIn()}>
            <Icon name="plus" size={20} />
          </button>
          <button type="button" aria-label="Alejar" onClick={() => map.current?.zoomOut()}>
            <Icon name="minus" size={20} />
          </button>
        </div>
      </div>

      <div className="m-sheet">
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
                <span>
                  {estado.label} · {camion.updated ? ago(camion.updated) : 'Sin señal'}
                </span>
              </div>
              <div className="m-sheet__speed">
                <b>{velocidad}</b>
                <span>km/h</span>
              </div>
            </button>
            <div className="m-sheet__foot">
              <span>
                {visibleTrucks.length} de {trucks.length} camiones
              </span>
              <button
                className="m-btn-dark"
                type="button"
                onClick={() => navigate('/fleet')}
              >
                Ver flota
                <Icon name="chevronUp" size={16} stroke={2.2} />
              </button>
            </div>
          </>
        ) : (
          <p className="m-sheet__empty">Todavía no hay camiones en la flota.</p>
        )}
      </div>
    </section>
  );
}
