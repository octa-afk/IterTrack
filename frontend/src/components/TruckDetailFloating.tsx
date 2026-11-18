import { useDashboard } from '../state/useDashboard';
import { TruckDetail } from './TruckDetail';

/*
 * Tarjeta del camión sobre el mapa: fija, arriba, en el centro de la superficie
 * libre entre el lateral y el panel de flota. No se arrastra ni se recoloca:
 * ni sigue al camión, ni cambia al elegir otro, ni se corre al panear o hacer
 * zoom. Su lugar lo fija el CSS (`.truck-float`), sin medir nada en el DOM.
 *
 * Aparece sólo con un camión seleccionado.
 */
export function TruckDetailFloating() {
  const { selectedTruck } = useDashboard();

  if (selectedTruck === null) return null;

  return (
    <div className="truck-float">
      <TruckDetail />
    </div>
  );
}
