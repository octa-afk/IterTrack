import { useDashboard } from '../state/useDashboard';

/*
 * Buscador de flota. Vive donde se ve la flota —el panel derecho del mapa y la
 * tabla de Camiones— y escribe `filters.q`, el mismo filtro que ya usan la lista
 * y los marcadores del mapa: buscar en el panel filtra las dos cosas a la vez.
 */
export function FleetSearch() {
  const { filters, setFilter } = useDashboard();

  return (
    <label className="fleet-search">
      <input
        type="search"
        placeholder="Buscar patente o chofer"
        aria-label="Buscar camiones"
        value={filters.q}
        onChange={(e) => setFilter({ q: e.target.value })}
      />
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" />
      </svg>
    </label>
  );
}
