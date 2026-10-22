// Pure telemetry transformations shared by polling and rendering orchestration.
export function applyTelemetryPoint(t, p, { haversineM, bearing, programarMovimiento, estadoDe, historyMax }) {
  const lat = p.lat, lng = p.long;
  const ts = Date.parse(p.timestamp) || Date.now();
  const previous = t.lat === null ? null : [t.lat, t.lng];
  if (previous) {
    const dtMs = ts - t.updated;
    const distance = haversineM(previous[0], previous[1], lat, lng);
    if (dtMs > 0) t.speed = Math.max(0, Math.min(200, Math.round((distance / (dtMs / 1000)) * 3.6)));
    if (distance > 5) t.heading = bearing(previous[0], previous[1], lat, lng);
    programarMovimiento(t, previous, [lat, lng], dtMs);
  }
  t.lat = lat; t.lng = lng; t.updated = ts;
  t.history.push(t.speed);
  if (t.history.length > historyMax) t.history.shift();
  t.status = estadoDe(t);
}

export function buildHistory(points, { haversineM, historyMax }) {
  const chronological = points.slice().reverse();
  const history = [];
  for (let i = 1; i < chronological.length; i++) {
    const current = chronological[i], previous = chronological[i - 1];
    const seconds = (Date.parse(current.recorded_at) - Date.parse(previous.recorded_at)) / 1000;
    const distance = haversineM(previous.lat, previous.long, current.lat, current.long);
    history.push(seconds > 0 ? Math.max(0, Math.min(200, Math.round((distance / seconds) * 3.6))) : 0);
  }
  return history.slice(-historyMax);
}
