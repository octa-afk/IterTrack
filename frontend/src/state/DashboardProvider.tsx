import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, clearToken, getToken } from '../api/client';
import { me } from '../api/auth';
import { getHistory, listLiveTrucks } from '../api/trucks';
import {
  DEFAULT_FILTERS,
  POLL_MS,
  TRIP_LIMIT,
  aplicarEstado,
  buildHistory,
  crearEstadoCamion,
  filterAndSortTrucks,
  type Filters,
  type TruckState,
} from '../lib/trucks';
import { DashboardContext, type DashboardState } from './DashboardContext';
import { iniciarPolling, type Polling } from './polling';

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
    let polling: Polling | undefined;

    async function refresh() {
      try {
        // Un solo pedido para toda la flota (antes: 1 + uno por camión).
        const data = await listLiveTrucks();
        if (cancelled) return;
        setTrucks((prev) => {
          const existing = new Map(prev.map((t) => [t.id, t]));
          return data.map((live) =>
            aplicarEstado(existing.get(live.id) ?? crearEstadoCamion(live), live),
          );
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
      if (cancelled) return;
      setReady(true);
      // Un solo poller de flota, que no consulta con la pestaña oculta.
      polling = iniciarPolling(refresh, POLL_MS, { inmediato: false });
    }

    void boot();

    return () => {
      cancelled = true;
      polling?.detener();
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
        setTrucks((prev) =>
          prev.map((truck) =>
            truck.id === id
              ? { ...truck, history: history.length ? history : truck.history }
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
    /*
     * "Ver recorrido" desde Rutas: selecciona el camión y su traza aparece en
     * el mapa. No hay un segundo estado que encender —la traza siempre es la
     * del camión seleccionado—, así que no puede quedar la del anterior.
     */
    verRecorrido: (id) => select(id),
    setFilter: (patch) => setFilters((f) => ({ ...f, ...patch })),
  };

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}
