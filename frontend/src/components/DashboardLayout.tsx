import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';
import { DashboardProvider } from '../state/DashboardProvider';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
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
      <div className={navOpen ? 'app' : 'app nav-off'}>
        <Sidebar onLogout={handleLogout} />
        <div className="content">
          <Topbar navOpen={navOpen} onToggleNav={toggleNav} />
          <div className={enPanel ? 'mapbox' : 'mapbox mapbox-off'} aria-hidden={!enPanel}>
            <MapView />
          </div>
          <Outlet />
        </div>
      </div>
    </DashboardProvider>
  );
}
