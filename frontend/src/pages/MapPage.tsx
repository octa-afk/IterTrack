import { FleetList } from '../components/FleetList';
import { TruckDetailFloating } from '../components/TruckDetailFloating';

/*
 * Panel de escritorio: las tarjetas flotantes sobre el mapa en vivo. El mapa y
 * el shell (sidebar, provider) los aporta `DashboardLayout`, que los mantiene
 * montados entre secciones. En un dispositivo móvil el panel lo resuelve
 * `MobileLayout`, así que esta página nunca se monta ahí.
 */
export default function MapPage() {
  return (
    <div className="grid">
      <div className="col">
        <TruckDetailFloating />
      </div>
      <div className="col">
        <FleetList />
      </div>
    </div>
  );
}
