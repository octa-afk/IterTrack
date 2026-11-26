/*
 * Isotipo «Perímetro» de IterTrack, compartido por el lateral, la pastilla del
 * mapa, el menú móvil y el registro. Es la versión para tamaños chicos, con los
 * colores incluidos sobre su cuadrado azul noche: se ve igual sobre cualquier
 * fondo. Mismo dibujo que `assets/favicon.svg`.
 */
export function Mark({ decorative = false }: { decorative?: boolean }) {
  return (
    <svg
      className="mark"
      viewBox="0 0 200 200"
      {...(decorative
        ? { 'aria-hidden': true }
        : { role: 'img', 'aria-label': 'IterTrack' })}
    >
      <rect width="200" height="200" rx="46" fill="#0b1b3f" />
      <circle cx="100" cy="100" r="26" fill="#ffffff" />
      <path
        d="M108.29 167.49A68 68 0 1 1 167.49 108.29"
        fill="none"
        stroke="#6a8cee"
        strokeWidth="20"
        strokeLinecap="round"
      />
      <circle cx="148.08" cy="148.08" r="21" fill="#2fd6bd" />
    </svg>
  );
}
