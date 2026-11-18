import { useEffect, useState } from 'react';

/**
 * Suscripción a un `matchMedia` con estado reactivo.
 *
 * El layout móvil se elige por capacidades del dispositivo (puntero táctil sin
 * hover), no por ancho ni por user agent: la misma build sirve la UI táctil en
 * un teléfono y el dashboard en una PC, aunque la ventana de la PC sea angosta.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}
