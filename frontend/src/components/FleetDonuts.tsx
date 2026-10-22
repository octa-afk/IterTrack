import { isFresh, type TruckState } from '../lib/trucks';

/*
 * Ported from renderFleetDonuts() in source/static/js/truck-charts.js.
 * Fuel is not exposed by the backend, so that ring stays at "--" exactly like
 * the vanilla dashboard.
 */
const RADIUS = 27;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function Donut({
  pct,
  color,
  label,
  value,
  center,
}: {
  pct: number;
  color: string;
  label: string;
  value: string;
  center?: string;
}) {
  const pctText = center ?? `${Math.round(pct)}%`;
  return (
    <div className="dn">
      <div style={{ position: 'relative' }}>
        <svg viewBox="0 0 68 68">
          <circle cx="34" cy="34" r={RADIUS} stroke="#e9ebe8" />
          <circle
            cx="34"
            cy="34"
            r={RADIUS}
            stroke={color}
            strokeLinecap="round"
            strokeDasharray={`${(CIRCUMFERENCE * pct) / 100} ${CIRCUMFERENCE}`}
          />
        </svg>
        <div className="pc" style={{ color }}>
          {pctText}
        </div>
      </div>
      <div className="t">
        {label}
        <b>{value}</b>
      </div>
    </div>
  );
}

export function FleetDonuts({ trucks }: { trucks: TruckState[] }) {
  const total = trucks.length || 1;
  const moving = trucks.filter((t) => t.status === 'move' || t.status === 'alert').length;
  const fresh = trucks.filter((t) => isFresh(t.updated)).length;

  return (
    <div className="donuts">
      <Donut
        pct={(moving / total) * 100}
        color="#eeb04a"
        label="En ruta"
        value={`${moving} de ${total}`}
      />
      <Donut pct={0} color="#9a8fd6" label="Combustible" value="promedio" center="—" />
      <Donut
        pct={(fresh / total) * 100}
        color="#7fa0e8"
        label="Con señal"
        value={`${fresh} de ${total}`}
      />
    </div>
  );
}
