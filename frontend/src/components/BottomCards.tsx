import { useDashboard } from '../state/useDashboard';
import { SpeedBars } from './SpeedBars';
import { FleetDonuts } from './FleetDonuts';

/*
 * The bottom row of the dashboard (speed bars + fleet summary). It reads the
 * dashboard context itself so MapPage does not need to thread state through.
 */
export function BottomCards() {
  const { trucks, visibleTrucks, selectedId, select } = useDashboard();

  return (
    <div className="bottom">
      <div className="card">
        <div className="card-h">
          <h3>Velocidad por camión</h3>
          <span className="tag">Ahora</span>
        </div>
        <SpeedBars trucks={visibleTrucks} selectedId={selectedId} onSelect={select} />
      </div>
      <div className="card">
        <h3>Resumen de flota</h3>
        <FleetDonuts trucks={trucks} />
      </div>
    </div>
  );
}
