/*
 * Ported from source/static/js/truck-movement.js.
 * Tweens every marker between the previous and the new polled coordinate so
 * trucks glide instead of jumping once per poll.
 */
export type LatLngTuple = [number, number];

export interface MovableMarker {
  setLatLng(latlng: LatLngTuple): unknown;
}

export interface ActiveMove {
  from: LatLngTuple;
  to: LatLngTuple;
  start: number;
  duration: number;
}

export interface MovementControllerOptions {
  moves: Map<number, ActiveMove>;
  markers: Map<number, MovableMarker>;
  minDuration: number;
  maxDuration: number;
  defaultDuration: number;
  ease: (k: number) => number;
  distance: (aLat: number, aLng: number, bLat: number, bLng: number) => number;
}

export interface MovementController {
  programarMovimiento(
    truck: { id: number },
    from: LatLngTuple,
    to: LatLngTuple,
    elapsed: number,
  ): void;
  stop(): void;
}

export function createMovementController({
  moves,
  markers,
  minDuration,
  maxDuration,
  defaultDuration,
  ease,
  distance,
}: MovementControllerOptions): MovementController {
  let animationFrame: number | null = null;

  function tick() {
    animationFrame = null;
    const now = performance.now();
    let active = false;
    moves.forEach((move, id) => {
      const progress = Math.min(1, (now - move.start) / move.duration);
      const eased = ease(progress);
      const marker = markers.get(id);
      if (marker) {
        marker.setLatLng([
          move.from[0] + (move.to[0] - move.from[0]) * eased,
          move.from[1] + (move.to[1] - move.from[1]) * eased,
        ]);
      }
      if (progress < 1) active = true;
      else moves.delete(id);
    });
    if (active) animationFrame = requestAnimationFrame(tick);
  }

  function wake() {
    if (animationFrame === null) animationFrame = requestAnimationFrame(tick);
  }

  function programarMovimiento(
    truck: { id: number },
    from: LatLngTuple,
    to: LatLngTuple,
    elapsed: number,
  ) {
    if (distance(from[0], from[1], to[0], to[1]) < 5) {
      moves.delete(truck.id);
      return;
    }
    const duration = Math.max(
      minDuration,
      Math.min(maxDuration, elapsed > 0 ? elapsed : defaultDuration),
    );
    moves.set(truck.id, { from, to, start: performance.now(), duration });
    wake();
  }

  function stop() {
    if (animationFrame !== null) {
      cancelAnimationFrame(animationFrame);
      animationFrame = null;
    }
    moves.clear();
  }

  return { programarMovimiento, stop };
}
