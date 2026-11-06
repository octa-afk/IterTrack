import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { mapaActual } from '../lib/mapHandle';
import { useDashboard } from '../state/useDashboard';
import { TruckDetail } from './TruckDetail';

/*
 * Tarjeta del camión flotando sobre el mapa. Aparece una sola vez, al lado del
 * vehículo, y desde ahí **no se mueve sola**: ni sigue al camión cuando avanza,
 * ni salta al elegir otro camión, ni se corre al panear o hacer zoom. La única
 * mano que la mueve es la del operador, arrastrándola.
 *
 * Por eso la colocación inicial se calcula una sola vez y se olvida: cualquier
 * recolocación automática después de aparecer vuelve a convertirla en algo que
 * se escapa de abajo del puntero.
 */
const MARGEN = 16;
/** Separación entre el camión y la tarjeta al colocarla. */
const SEPARACION = 52;

interface Posicion {
  x: number;
  y: number;
}

interface Rectangulo {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/*
 * Dónde poner la tarjeta para que quede cerca del camión sin tapar el lateral
 * ni el panel de flota: se prueban los cuatro lados y gana el primero que entra
 * entero en la superficie libre del mapa. Si ninguno entra (ventana angosta), se
 * centra en el camión y se recorta a los bordes.
 */
function cercaDelCamion(
  camion: { x: number; y: number },
  tamano: { ancho: number; alto: number },
  libre: Rectangulo,
): Posicion {
  const entra = (x: number, y: number) =>
    x >= libre.left &&
    x + tamano.ancho <= libre.right &&
    y >= libre.top &&
    y + tamano.alto <= libre.bottom;

  const candidatos: Posicion[] = [
    { x: camion.x + SEPARACION, y: camion.y - tamano.alto / 2 },
    { x: camion.x - SEPARACION - tamano.ancho, y: camion.y - tamano.alto / 2 },
    { x: camion.x - tamano.ancho / 2, y: camion.y + SEPARACION },
    { x: camion.x - tamano.ancho / 2, y: camion.y - SEPARACION - tamano.alto },
  ];

  const elegido = candidatos.find((c) => entra(c.x, c.y));
  if (elegido) return elegido;

  return {
    x: Math.min(Math.max(camion.x - tamano.ancho / 2, libre.left), libre.right - tamano.ancho),
    y: Math.min(Math.max(camion.y - tamano.alto / 2, libre.top), libre.bottom - tamano.alto),
  };
}

function limitar({ x, y }: Posicion, ancho: number, alto: number): Posicion {
  const maxX = Math.max(MARGEN, window.innerWidth - ancho - MARGEN);
  const maxY = Math.max(MARGEN, window.innerHeight - alto - MARGEN);
  return {
    x: Math.min(Math.max(x, MARGEN), maxX),
    y: Math.min(Math.max(y, MARGEN), maxY),
  };
}

/** Superficie del mapa que no tapa ningún panel flotante. */
function superficieLibre(): Rectangulo {
  const lateral = document.querySelector('.side')?.getBoundingClientRect();
  const flota = document.querySelector('.grid > .col:last-child')?.getBoundingClientRect();
  return {
    left: lateral && lateral.width > 1 ? lateral.right + MARGEN : MARGEN,
    top: MARGEN,
    right: flota && flota.width > 1 ? flota.left - MARGEN : window.innerWidth - MARGEN,
    bottom: window.innerHeight - MARGEN,
  };
}

export function TruckDetailFloating() {
  const { selectedTruck } = useDashboard();
  const caja = useRef<HTMLDivElement>(null);
  const agarre = useRef<{ dx: number; dy: number } | null>(null);
  /** La tarjeta ya se colocó una vez: no vuelve a moverse sola. */
  const colocada = useRef(false);
  const [posicion, setPosicion] = useState<Posicion | null>(null);
  const [arrastrando, setArrastrando] = useState(false);

  const id = selectedTruck?.id ?? null;

  const colocar = () => {
    const el = caja.current;
    if (!el) return false;

    const ancho = el.offsetWidth;
    const alto = el.offsetHeight;
    const map = mapaActual();
    const cajaMapa = map?.getContainer().getBoundingClientRect();
    let posicion: Posicion;

    if (map && cajaMapa && cajaMapa.width > 0 && cajaMapa.height > 0) {
      /*
       * El mapa vuela al camión al seleccionarlo, así que después del vuelo el
       * vehículo queda en el centro del mapa: ésa es la referencia para dejar la
       * tarjeta al lado sin esperar a que termine la animación (si se esperara,
       * la tarjeta se movería después de aparecer).
       */
      const tamano = map.getSize();
      posicion = cercaDelCamion(
        { x: cajaMapa.left + tamano.x / 2, y: cajaMapa.top + tamano.y / 2 },
        { ancho, alto },
        superficieLibre(),
      );
    } else {
      /* Sin mapa montado o sin tamaño: rincón inferior izquierdo del mapa. */
      posicion = { x: MARGEN + 260, y: window.innerHeight - alto - 90 };
    }

    setPosicion(limitar(posicion, ancho, alto));
    return true;
  };

  /* Colocación única: la primera vez que hay un camión y una caja que medir. */
  useLayoutEffect(() => {
    if (id === null || colocada.current) return;
    colocada.current = colocar();
    // `colocar` sólo depende del DOM; no se recalcula con el camión ni el mapa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  /* Al cambiar el tamaño de la ventana, la tarjeta vuelve a entrar. */
  useEffect(() => {
    const alRedimensionar = () => {
      const el = caja.current;
      if (!el) return;
      const marco = el.getBoundingClientRect();
      setPosicion(limitar({ x: marco.left, y: marco.top }, marco.width, marco.height));
    };
    window.addEventListener('resize', alRedimensionar);
    return () => window.removeEventListener('resize', alRedimensionar);
  }, []);

  const empezarArrastre = (evento: ReactPointerEvent<HTMLDivElement>) => {
    /* Los controles de la tarjeta siguen siendo clicables. */
    if ((evento.target as HTMLElement).closest('button, a, input, select, textarea')) {
      return;
    }
    const el = caja.current;
    if (!el) return;
    const marco = el.getBoundingClientRect();
    agarre.current = { dx: evento.clientX - marco.left, dy: evento.clientY - marco.top };
    el.setPointerCapture(evento.pointerId);
    setArrastrando(true);
  };

  const moverArrastre = (evento: ReactPointerEvent<HTMLDivElement>) => {
    const desde = agarre.current;
    const el = caja.current;
    if (!desde || !el) return;
    setPosicion(
      limitar(
        { x: evento.clientX - desde.dx, y: evento.clientY - desde.dy },
        el.offsetWidth,
        el.offsetHeight,
      ),
    );
  };

  const soltarArrastre = (evento: ReactPointerEvent<HTMLDivElement>) => {
    if (!agarre.current) return;
    agarre.current = null;
    setArrastrando(false);
    caja.current?.releasePointerCapture(evento.pointerId);
  };

  if (selectedTruck === null) return null;

  /*
   * La caja se monta siempre que haya un camión elegido, aunque todavía no
   * tenga posición: el efecto de colocación necesita medirla. Hasta que la
   * posición está calculada queda invisible.
   */
  return (
    <div
      ref={caja}
      className={`truck-float${arrastrando ? ' is-dragging' : ''}`}
      style={{
        left: posicion?.x ?? 0,
        top: posicion?.y ?? 0,
        visibility: posicion === null ? 'hidden' : 'visible',
      }}
      onPointerDown={empezarArrastre}
      onPointerMove={moverArrastre}
      onPointerUp={soltarArrastre}
      onPointerCancel={soltarArrastre}
    >
      <TruckDetail />
    </div>
  );
}
