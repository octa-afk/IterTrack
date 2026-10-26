import { FleetList } from '../components/FleetList';
import { TruckDetail } from '../components/TruckDetail';

/*
 * Panel de escritorio: las tarjetas flotantes sobre el mapa en vivo. El mapa y
 * el shell (sidebar, topbar, provider) los aporta `DashboardLayout`, que los
 * mantiene montados entre secciones. Por debajo de 640 px el panel móvil lo
 * resuelve `MobileLayout`, así que esta página nunca se monta ahí.
 */
export default function MapPage() {
  return (
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
  );
}
