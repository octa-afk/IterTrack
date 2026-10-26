import { useEffect, useState } from 'react';

/**
 * Suscripción a un `matchMedia` con estado reactivo.
 *
 * El layout móvil se elige por ancho de teléfono, no por user agent: la misma
 * build sirve la UI táctil en un teléfono y el dashboard en una PC. El
 * breakpoint es el que ya fija `tests/test_static_css.py` (640 px).
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
