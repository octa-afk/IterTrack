import { FleetList } from '../components/FleetList';
import { Mark } from '../components/Mark';

/*
 * Panel de escritorio: la pastilla «Mapa en vivo» y el panel de flota flotando
 * sobre el mapa. El mapa y el shell (sidebar, provider) los aporta
 * `DashboardLayout`, que los mantiene montados entre secciones. En un
 * dispositivo móvil el panel lo resuelve `MobileLayout`, así que esta página
 * nunca se monta ahí.
 *
 * La pastilla lleva el logo de IterTrack sólo con el lateral plegado (lo decide
 * el CSS), para que la marca no aparezca dos veces. El detalle del camión
 * elegido no es una tarjeta aparte: se despliega dentro de su fila en la lista
 * (`FleetList`).
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
      </div>
      <div className="col">
        <FleetList />
      </div>
    </div>
  );
}
