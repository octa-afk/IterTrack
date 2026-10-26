import { useCallback, useRef, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { Map as LeafletMap } from 'leaflet';
import { clearToken } from '../api/client';
import MapView from '../components/MapView';
import { DashboardProvider } from '../state/DashboardProvider';
import { MobileDrawer } from './MobileDrawer';
import type { MobileOutletContext } from './context';

/*
 * Shell de la SPA por debajo del ancho de teléfono.
 *
 * Igual que el layout de escritorio, el provider de la flota vive acá y no en
 * cada pantalla: cambiar de sección no reinicia el polling. El mapa también se
 * monta una sola vez y al salir del panel se oculta con `mapbox-off` —que a
 * este ancho es `display:none`— en lugar de desmontarse, así no se recrean
 * Leaflet + MapLibre ni se vuelve a pedir el estilo de OpenFreeMap.
 */
export function MobileLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mapRef = useRef<LeafletMap | null>(null);
  const enPanel = pathname === '/map';

  const handleReady = useCallback((map: LeafletMap) => {
    mapRef.current = map;
  }, []);

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const handleLogout = () => {
    clearToken();
    navigate('/');
  };

  const outletContext: MobileOutletContext = { map: mapRef, openDrawer };

  return (
    <DashboardProvider>
      <div className="m-app">
        <div className={enPanel ? 'mapbox' : 'mapbox mapbox-off'} aria-hidden={!enPanel}>
          <MapView onReady={handleReady} showZoomControl={false} />
        </div>

        <div className="m-content">
          <Outlet context={outletContext} />
        </div>

        <MobileDrawer open={drawerOpen} onClose={closeDrawer} onLogout={handleLogout} />
      </div>
    </DashboardProvider>
  );
}
