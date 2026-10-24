import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, clearToken, getToken } from '../api/client';
import { me } from '../api/auth';
import { getHistory, getLocation, listTrucks } from '../api/trucks';
import {
  DEFAULT_FILTERS,
  POLL_MS,
  TRIP_LIMIT,
  appendPath,
  aplicarPunto,
  buildHistory,
  buildPath,
  crearEstadoCamion,
  filterAndSortTrucks,
  type Filters,
  type TruckState,
} from '../lib/trucks';
import { DashboardContext, type DashboardState } from './DashboardContext';

export function DashboardProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [trucks, setTrucks] = useState<TruckState[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [userInitials, setUserInitials] = useState('FL');
  const [role, setRole] = useState('member');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let interval: number | undefined;

    async function refresh() {
      try {
        const data = await listTrucks();
        const locations = await Promise.all(
          data.map((t) => getLocation(t.id).catch(() => null)),
        );
        if (cancelled) return;
        setTrucks((prev) => {
          const existing = new Map(prev.map((t) => [t.id, t]));
          return data.map((truck) => {
            const known = existing.get(truck.id);
            const base = known
              ? { ...known, plate: truck.plate, active: truck.active }
              : crearEstadoCamion(truck);
            const point = locations.find((p) => p && p.truck_id === truck.id);
            if (!point) return base;
            const clone = {
              ...base,
              history: [...base.history],
              path: appendPath(base.path, point),
            };
            aplicarPunto(clone, point);
            return clone;
          });
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearToken();
          navigate('/');
        }
      }
    }

    async function boot() {
      if (!getToken()) {
        navigate('/');
        return;
      }
      try {
        const user = await me();
        if (!cancelled) {
          setUserInitials(String(user.username || 'FL').slice(0, 2).toUpperCase());
          setRole(user.role || 'member');
        }
      } catch {
        clearToken();
        navigate('/');
        return;
      }
      await refresh();
      if (!cancelled) setReady(true);
      interval = window.setInterval(() => {
        void refresh();
      }, POLL_MS);
    }

    void boot();

    return () => {
      cancelled = true;
      if (interval !== undefined) window.clearInterval(interval);
    };
  }, [navigate]);

  const visibleTrucks = filterAndSortTrucks(trucks, filters);
  const selectedTruck = trucks.find((t) => t.id === selectedId) ?? null;

  /*
   * GET /trucks/{id}/iter -> real speed history for the detail sparkline and
   * the trail drawn on the map. Polling appends new points to the same trail.
   */
  const select = (id: number) => {
    setSelectedId(id);
    void (async () => {
      try {
        const points = await getHistory(id, TRIP_LIMIT);
        const history = buildHistory(points);
        const path = buildPath(points);
        setTrucks((prev) =>
          prev.map((truck) =>
            truck.id === id
              ? {
                  ...truck,
                  history: history.length ? history : truck.history,
                  path,
                }
              : truck,
          ),
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearToken();
          navigate('/');
        }
      }
    })();
  };

  const value: DashboardState = {
    trucks,
    selectedId,
    filters,
    userInitials,
    role,
    ready,
    visibleTrucks,
    selectedTruck,
    select,
    setFilter: (patch) => setFilters((f) => ({ ...f, ...patch })),
  };

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}
