export function createMovementController({ moves, markers, minDuration, maxDuration, defaultDuration, ease, distance }) {
  let animationFrame = null;
  function tick() {
    animationFrame = null;
    const now = performance.now();
    let active = false;
    moves.forEach((move, id) => {
      const progress = Math.min(1, (now - move.start) / move.duration);
      const eased = ease(progress);
      const marker = markers.get(id);
      if (marker) marker.setLatLng([move.from[0] + (move.to[0] - move.from[0]) * eased, move.from[1] + (move.to[1] - move.from[1]) * eased]);
      if (progress < 1) active = true; else moves.delete(id);
    });
    if (active) animationFrame = requestAnimationFrame(tick);
  }
  function wake() { if (animationFrame === null) animationFrame = requestAnimationFrame(tick); }
  function programarMovimiento(truck, from, to, elapsed) {
    if (distance(from[0], from[1], to[0], to[1]) < 5) { moves.delete(truck.id); return; }
    const duration = Math.max(minDuration, Math.min(maxDuration, elapsed > 0 ? elapsed : defaultDuration));
    moves.set(truck.id, { from, to, start: performance.now(), duration });
    wake();
  }
  return { programarMovimiento };
}
