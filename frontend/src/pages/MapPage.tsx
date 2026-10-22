import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Topbar } from '../components/Topbar';
import { MobileTabs } from '../components/MobileTabs';
import { FleetList } from '../components/FleetList';
import MapView from '../components/MapView';
import { TruckDetail } from '../components/TruckDetail';
import { clearToken } from '../api/client';
import { DashboardProvider } from '../state/DashboardProvider';

const NAV_KEY = 'itertrack-nav';

export default function MapPage() {
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(() => localStorage.getItem(NAV_KEY) !== '0');
  const [mobileView, setMobileView] = useState('map');

  useEffect(() => {
    document.body.dataset.mobileView = mobileView;
    return () => {
      delete document.body.dataset.mobileView;
    };
  }, [mobileView]);

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
          <div className="grid">
            <div className="col">
              <div className="card mapcard">
                <div className="card-h">
                  <h3>Mapa en vivo</h3>
                  <span className="tag" id="liveTag">
                    Actualizando
                  </span>
                </div>
                <div className="mapbox">
                  <MapView />
                </div>
              </div>
              <div className="bottom">
                <div className="card">
                  <div className="card-h">
                    <h3>Velocidad por camión</h3>
                    <span className="tag">Ahora</span>
                  </div>
                  <div className="bars" id="bars" />
                </div>
                <div className="card">
                  <h3>Resumen de flota</h3>
                  <div className="donuts" id="donuts" />
                </div>
              </div>
            </div>
            <div className="col">
              <FleetList />
              <TruckDetail />
            </div>
          </div>
        </div>
      </div>
      <MobileTabs view={mobileView} onChange={setMobileView} />
    </DashboardProvider>
  );
}
