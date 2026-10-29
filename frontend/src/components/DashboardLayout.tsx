import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';
import { DashboardProvider } from '../state/DashboardProvider';
import { Sidebar } from './Sidebar';
import MapView from './MapView';

const NAV_KEY = 'itertrack-nav';

/*
 * Shell de las secciones autenticadas. El provider de la flota vive acá, no en
 * cada página: cambiar de sección no reinicia el polling ni pierde la selección.
 *
 * El mapa también vive acá y se monta una sola vez. Si lo montara la página del
 * panel, cada visita recrearía Leaflet + MapLibre y volvería a pedir el estilo
 * de OpenFreeMap; al cambiar de sección sólo se oculta con `visibility`, que
 * conserva el tamaño (Leaflet no necesita invalidateSize) y el estado.
 *
 * No hay barra superior: la búsqueda y el perfil viven en el lateral, y los
 * paneles flotantes arrancan en el borde de arriba. Eso devuelve al mapa los
 * 64 px de alto que ocupaba la barra.
 */
export function DashboardLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(() => localStorage.getItem(NAV_KEY) !== '0');
  const enPanel = pathname === '/map';

  const toggleNav = () => {
    setNavOpen((open) => {
      const next = !open;
      try {
        localStorage.setItem(NAV_KEY, next ? '1' : '0');
      } catch {
        /* localStorage unavailable: keep the in-memory state only */
      }
      return next;
    });
  };

  const handleLogout = () => {
    clearToken();
    navigate('/');
  };

  return (
    <DashboardProvider>
      <div className={`app${navOpen ? '' : ' nav-off'}${enPanel ? '' : ' app-section'}`}>
        <Sidebar navOpen={navOpen} onToggleNav={toggleNav} onLogout={handleLogout} />
        {/*
         * Con el lateral plegado no queda ningún botón visible para volver a
         * abrirlo: éste flota sobre el mapa, en la esquina que deja libre el
         * encabezado del panel.
         */}
        <button
          className="navtoggle side-reopen"
          type="button"
          aria-controls="sidebar"
          aria-expanded={false}
          aria-label="Mostrar panel lateral"
          title="Mostrar panel lateral"
          onClick={toggleNav}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="3" />
            <path d="M9 4v16" />
          </svg>
        </button>
        <div className="content">
          <div className={enPanel ? 'mapbox' : 'mapbox mapbox-off'} aria-hidden={!enPanel}>
            <MapView />
          </div>
          <Outlet />
        </div>
      </div>
    </DashboardProvider>
  );
}
