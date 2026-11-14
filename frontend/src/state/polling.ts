/*
 * Un solo mecanismo de polling para toda la app.
 *
 * Antes cada componente tenía su `setInterval`: seguía consultando con la
 * pestaña en segundo plano y, si la API tardaba más que el intervalo, dos
 * pedidos se cruzaban y el más viejo podía pisar al más nuevo.
 */

export interface Polling {
  /** Corre la tarea ya (si no hay una en curso), sin esperar al próximo latido. */
  ahora(): void;
  detener(): void;
}

/**
 * Ejecuta `tarea` ahora y después cada `intervaloMs`.
 *
 * - Nunca hay dos ejecuciones a la vez: el próximo latido se programa cuando
 *   termina el anterior.
 * - Con la pestaña oculta no consulta; al volver, consulta en el acto para no
 *   mostrar datos viejos.
 * - `inmediato: false` arranca en el próximo latido (el llamador ya consultó).
 */
export function iniciarPolling(
  tarea: () => Promise<void>,
  intervaloMs: number,
  { inmediato = true }: { inmediato?: boolean } = {},
): Polling {
  let detenido = false;
  let enCurso = false;
  let timer: number | undefined;

  const programar = () => {
    window.clearTimeout(timer);
    if (detenido || document.hidden) return;
    timer = window.setTimeout(() => void correr(), intervaloMs);
  };

  async function correr() {
    if (detenido || enCurso) return;
    enCurso = true;
    window.clearTimeout(timer);
    try {
      await tarea();
    } catch {
      // Cada tarea maneja sus errores; un fallo no puede cortar el polling.
    } finally {
      enCurso = false;
    }
    programar();
  }

  const alCambiarVisibilidad = () => {
    if (document.hidden) window.clearTimeout(timer);
    else void correr();
  };

  document.addEventListener('visibilitychange', alCambiarVisibilidad);
  if (inmediato) void correr();
  else programar();

  return {
    ahora: () => void correr(),
    detener: () => {
      detenido = true;
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', alCambiarVisibilidad);
    },
  };
}
