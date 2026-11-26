/*
 * Isotipo «Perímetro» de IterTrack, sin fondo, compartido por el lateral, la
 * pastilla del mapa, el menú móvil y el registro. Los colores son los de fondos
 * claros; sobre fondos oscuros se cambian con las variables `--mark-*`.
 */
export function Mark({ decorative = false }: { decorative?: boolean }) {
  return (
    <svg
      className="mark"
      viewBox="12 12 176 176"
      {...(decorative
        ? { 'aria-hidden': true }
        : { role: 'img', 'aria-label': 'IterTrack' })}
    >
      <circle cx="100" cy="100" r="19" style={{ fill: 'var(--mark-center, #0b1b3f)' }} />
      <circle
        cx="100"
        cy="100"
        r="43"
        strokeWidth="13"
        style={{ fill: 'none', stroke: 'var(--mark-inner, #2a52c4)' }}
      />
      <path
        d="M115.39 172.38A74 74 0 1 1 172.38 115.39"
        strokeWidth="13"
        strokeLinecap="round"
        style={{ fill: 'none', stroke: 'var(--mark-outer, #6a8cee)' }}
      />
      <circle cx="152.33" cy="152.33" r="15" style={{ fill: 'var(--mark-signal, #0f9c88)' }} />
    </svg>
  );
}
