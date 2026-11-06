import { SPEED_LIMIT } from '../lib/trucks';

/*
 * Speed-history sparkline, ported from buildSparkline() in
 * source/static/js/truck-charts.js (rendered as JSX instead of an HTML string).
 */
export function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return null;

  const width = 300;
  const height = 64;
  const max = Math.max(120, ...data);
  const x = (i: number) => (i * width) / (data.length - 1);
  const y = (v: number) => height - 4 - ((height - 10) * v) / max;

  const points = data.map((v, i) => [x(i), y(v)] as const);
  let path = `M${points[0][0]},${points[0][1]}`;
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    const center = (x0 + x1) / 2;
    path += ` C${center},${y0} ${center},${y1} ${x1},${y1}`;
  }
  const limitY = y(SPEED_LIMIT);

  return (
    <svg
      className="spark"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-label="Velocidad reciente"
    >
      <line x1="0" y1={limitY} x2={width} y2={limitY} stroke="#eeb04a" strokeDasharray="4 4" strokeWidth="1" />
      <path d={path} fill="none" stroke="#5a7ee6" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
