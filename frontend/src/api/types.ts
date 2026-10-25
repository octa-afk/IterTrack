/*
 * Types mirroring the FastAPI contract:
 *   - source/schemas/auth.py   -> UserCreate, UserResponse, Token
 *   - source/schemas/truck.py  -> Truck shape
 *   - source/models/truck.py   -> Truck, TrackingPoint ORM columns
 *
 * These are the single source of truth for the typed API client. Keep them in
 * sync with the backend schemas when the contract changes.
 */

// ---- Auth (source/schemas/auth.py) ----

export interface UserCreate {
  username: string;
  email: string;
  full_name: string;
  password: string;
  invitation_code: string;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string;
  full_name: string;
  disabled: boolean;
  /** `platform_admin` | `org_admin` | `member`. Decide si se ofrecen acciones. */
  role: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ---- Trucks (source/schemas/truck.py + source/models/truck.py) ----

/**
 * GET /trucks returns the ORM rows. `active` is the fleet-lifecycle flag: an
 * inactive truck keeps its history but the backend rejects new GPS reports.
 */
export interface Truck {
  id: number;
  plate: string;
  active: boolean;
}

/** A stored tracking point, as returned by /location and /iter. */
export interface TrackingPoint {
  id: number;
  truck_id: number;
  lat: number;
  long: number;
  speed: number;
  heading: number;
  timestamp: string;
  recorded_at: string;
  received_at: string;
}

/**
 * Public configuration served by GET /config.
 *
 * `demo.enabled` is decided by the deployment, not by the build: the same image
 * runs a real customer without the demo button.
 */
export interface DemoConfig {
  enabled: boolean;
  username?: string;
  password?: string;
}

export interface ClientConfig {
  demo: DemoConfig;
}


// ---- Destinos y viajes (source/schemas/destination.py) ----

export interface Charger {
  id: number;
  name: string;
  contact: string | null;
  active: boolean;
}

export interface Depot {
  id: number;
  name: string;
  lat: number;
  lng: number;
  radius_m: number;
}

export interface TripStop {
  id: number;
  seq: number;
  address: string;
  lat: number | null;
  lng: number | null;
  geo_source: string | null;
  geo_confidence: number | null;
  needs_review: boolean;
  receiver: string | null;
  status: string;
}

export interface Trip {
  id: number;
  charger_id: number;
  truck_id: number | null;
  driver_name: string | null;
  departure_at: string;
  depot_id: number | null;
  status: string;
  external_ref: string | null;
  notes: string | null;
  created_at: string;
  stops: TripStop[];
}

export interface TripCreatePayload {
  charger_id: number;
  departure_at: string;
  truck_id?: number | null;
  depot_id?: number | null;
  /** Reasigna el camión aunque tenga un viaje abierto (ese viaje se cancela). */
  replace_open_trip?: boolean;
  driver_name?: string | null;
  external_ref?: string | null;
  stops: { address: string; receiver?: string | null }[];
}
