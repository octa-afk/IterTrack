import { createContext } from 'react';
import type { Filters, TruckState } from '../lib/trucks';

export interface DashboardState {
  trucks: TruckState[];
  selectedId: number | null;
  filters: Filters;
  userInitials: string;
  ready: boolean;
  visibleTrucks: TruckState[];
  selectedTruck: TruckState | null;
  select: (id: number) => void;
  setFilter: (patch: Partial<Filters>) => void;
}

export const DashboardContext = createContext<DashboardState | null>(null);
