import { useEffect, useState } from 'react';
import { MobileTabs } from '../components/MobileTabs';
import { FleetList } from '../components/FleetList';
import { TruckDetail } from '../components/TruckDetail';

/*
 * Panel: las tarjetas flotantes sobre el mapa en vivo. El mapa y el shell
 * (sidebar, topbar, provider) los aporta `DashboardLayout`, que los mantiene
 * montados entre secciones.
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
          </div>
          <TruckDetail />
        </div>
        <div className="col">
          <FleetList />
        </div>
      </div>
      <MobileTabs view={mobileView} onChange={setMobileView} />
    </>
  );
}
