import { FleetList } from '../components/FleetList';
import { Mark } from '../components/Mark';
import { TruckDetailFloating } from '../components/TruckDetailFloating';

/*
 * Panel de escritorio: las tarjetas flotantes sobre el mapa en vivo. El mapa y
 * el shell (sidebar, provider) los aporta `DashboardLayout`, que los mantiene
 * montados entre secciones. Por debajo de 640 px el panel móvil lo resuelve
 * `MobileLayout`, así que esta página nunca se monta ahí.
 *
 * El encabezado lleva el logo sólo cuando el lateral está oculto: con el lateral
 * abierto la marca ya está a la vista y repetirla ensucia el mapa.
 */
export default function MapPage() {
  return (
    <div className="grid">
      <div className="col">
        <div className="card mapcard">
          <div className="card-h">
            <span className="map-mark">
              <Mark decorative />
            </span>
            <h3>Mapa en vivo</h3>
          </div>
        </div>
        <TruckDetailFloating />
      </div>
      <div className="col">
        <FleetList />
      </div>
    </div>
  );
}
