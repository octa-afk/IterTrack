import type { ReactNode } from 'react';

/*
 * Estado con ícono de color y sin fondo: la forma y el color van en el ícono y
 * la palabra queda en la tinta de cada pantalla. No se envuelve en una píldora
 * del mismo tono. Los colores viven en `styles/base.css` (`.st-ico`).
 */
export type StateKind =
  | 'move'
  | 'idle'
  | 'stop'
  | 'alert'
  | 'ok'
  | 'planned'
  | 'done'
  | 'cancelled';

const PATHS: Record<StateKind, ReactNode> = {
  move: <path d="M12 4l6.5 15L12 15.5 5.5 19z" />,
  idle: <path d="M9 6v12M15 6v12" />,
  stop: <path d="M12 4v8M7 7a7 7 0 1 0 10 0" />,
  alert: <path d="M12 4l9 16H3zM12 10v4M12 17.2v.1" />,
  ok: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  planned: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </>
  ),
  done: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  cancelled: <path d="M7 7l10 10M17 7L7 17" />,
};

/* Con `title` el ícono se anuncia solo; sin él acompaña a un texto y se oculta. */
export function StateIcon({ kind, title }: { kind: StateKind; title?: string }) {
  return (
    <svg
      className="st-ico"
      data-s={kind}
      viewBox="0 0 24 24"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {title && <title>{title}</title>}
      {PATHS[kind]}
    </svg>
  );
}
