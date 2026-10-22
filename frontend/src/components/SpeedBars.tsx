import { SPEED_LIMIT, type TruckState } from '../lib/trucks';

/*
 * Ported from renderSpeedBars() in source/static/js/truck-charts.js.
 * `height` is the plot area (129px card minus the 18px plate row).
 */
const MAX_SPEED = 120;
const PLOT_HEIGHT = 129 - 18;

const plateLabel = (plate: string) => String(plate).slice(0, 2) + String(plate).slice(-2);

export function SpeedBars({
  trucks,
  selectedId,
  onSelect,
}: {
  trucks: TruckState[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="bars">
      <div
        className="limit"
        style={{ bottom: 18 + (PLOT_HEIGHT * SPEED_LIMIT) / MAX_SPEED }}
      >
        <span>{`Límite ${SPEED_LIMIT} km/h`}</span>
      </div>
      {trucks.map((truck) => (
        <button
          key={truck.id}
          type="button"
          className={`bar ${truck.id === selectedId ? 'sel' : ''}`}
          title={`${truck.plate}: ${truck.speed} km/h`}
          onClick={() => onSelect(truck.id)}
        >
          <i style={{ height: Math.max(3.5, (PLOT_HEIGHT * truck.speed) / MAX_SPEED) }} />
          <b>{plateLabel(truck.plate)}</b>
        </button>
      ))}
    </div>
  );
}
