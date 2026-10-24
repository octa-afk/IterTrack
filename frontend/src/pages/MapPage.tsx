import { useEffect, useState } from 'react';
import { MobileTabs } from '../components/MobileTabs';
import MapView from '../components/MapView';
import { BottomCards } from '../components/BottomCards';
import { FleetList } from '../components/FleetList';
import { TruckDetail } from '../components/TruckDetail';

/*
 * Panel: mapa en vivo con la flota filtrable al costado. El shell (sidebar,
 * topbar, provider de estado) lo aporta `DashboardLayout`.
 */
export default function MapPage() {
  const [mobileView, setMobileView] = useState('map');

  useEffect(() => {
    document.body.dataset.mobileView = mobileView;
    return () => {
      delete document.body.dataset.mobileView;
    };
  }, [mobileView]);

  return (
    <>
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
          <BottomCards />
        </div>
        <div className="col">
          <FleetList />
          <TruckDetail />
        </div>
      </div>
      <MobileTabs view={mobileView} onChange={setMobileView} />
    </>
  );
}
