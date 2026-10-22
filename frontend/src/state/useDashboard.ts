import { useContext } from 'react';
import { DashboardContext, type DashboardState } from './DashboardContext';

export function useDashboard(): DashboardState {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within a DashboardProvider');
  return ctx;
}
