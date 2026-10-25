import { createContext } from 'react';
import type { Filters, TruckState } from '../lib/trucks';

export interface DashboardState {
  trucks: TruckState[];
  selectedId: number | null;
  filters: Filters;
  userInitials: string;
  /** Rol del usuario autenticado; `member` es de sólo lectura. */
  role: string;
  ready: boolean;
  visibleTrucks: TruckState[];
  selectedTruck: TruckState | null;
  /** Camión cuyo recorrido hecho se pidió ver desde Rutas; `null` = ninguno. */
  recorridoId: number | null;
  select: (id: number) => void;
  /** Selecciona el camión y habilita el trazo de su recorrido hecho en el mapa. */
  verRecorrido: (id: number) => void;
  setFilter: (patch: Partial<Filters>) => void;
}

export const DashboardContext = createContext<DashboardState | null>(null);
