import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { mapaActual } from '../lib/mapHandle';
import type { TruckState } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { TruckDetail } from './TruckDetail';

/*
 * Tarjeta del camión flotando sobre el mapa. Aparece sólo con un camión
 * seleccionado, arranca al lado del vehículo y se puede arrastrar.
 *
 * La posición es de pantalla, no del mapa: si la tarjeta se dibujara sobre la
 * capa del mapa se iría con cada paneo y no se podría leer. Mientras el
 * operador no la mueva, se recoloca al lado del camión cuando el mapa termina de
 * moverse (el vuelo al camión al seleccionarlo es lo que la dejaba lejos);
 * después de arrastrarla, manda el operador.
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

export function TruckDetailFloating() {
  const { selectedTruck } = useDashboard();
  const caja = useRef<HTMLDivElement>(null);
  const agarre = useRef<{ dx: number; dy: number } | null>(null);
  /** Una vez que el operador la movió, deja de seguir al camión. */
  const movida = useRef(false);
  const truckRef = useRef(selectedTruck);
  const [posicion, setPosicion] = useState<Posicion | null>(null);
  const [arrastrando, setArrastrando] = useState(false);

  const id = selectedTruck?.id ?? null;

  useEffect(() => {
    truckRef.current = selectedTruck;
  });

  const colocar = (truck: TruckState) => {
    const el = caja.current;
    if (!el || truck.lat === null || truck.lng === null) return;

    const ancho = el.offsetWidth;
    const alto = el.offsetHeight;
    const map = mapaActual();
    const cajaMapa = map?.getContainer().getBoundingClientRect();
    let posicion: Posicion;

    if (map && cajaMapa && cajaMapa.width > 0 && cajaMapa.height > 0) {
      const punto = map.latLngToContainerPoint([truck.lat, truck.lng]);
      /* Superficie del mapa que no tapa ningún panel flotante. */
      const lateral = document.querySelector('.side')?.getBoundingClientRect();
      const flota = document.querySelector('.grid > .col:last-child')?.getBoundingClientRect();
      const libre: Rectangulo = {
        left: lateral && lateral.width > 1 ? lateral.right + MARGEN : MARGEN,
        top: MARGEN,
        right: flota && flota.width > 1 ? flota.left - MARGEN : window.innerWidth - MARGEN,
        bottom: window.innerHeight - MARGEN,
      };
      posicion = cercaDelCamion(
        { x: cajaMapa.left + punto.x, y: cajaMapa.top + punto.y },
        { ancho, alto },
        libre,
      );
    } else {
      /* Sin mapa montado o sin tamaño: rincón inferior izquierdo del mapa. */
      posicion = { x: MARGEN + 260, y: window.innerHeight - alto - 90 };
    }

    setPosicion(limitar(posicion, ancho, alto));
  };

  /*
   * Colocación al elegir un camión y, mientras no se la haya arrastrado, cada
   * vez que el mapa termina de moverse: el vuelo al camión dura ~0.8 s y sin
   * esto la tarjeta quedaba donde estaba el camión antes del vuelo.
   */
  useLayoutEffect(() => {
    /* El camión del render, no el ref: el ref se actualiza en un efecto y en la
     * primera pasada todavía tendría el valor anterior. */
    const truck = selectedTruck;
    if (id === null || truck === null) return;
    movida.current = false;
    colocar(truck);

    const map = mapaActual();
    if (!map) return;
    const alTerminarDeMover = () => {
      const actual = truckRef.current ?? truck;
      if (movida.current) return;
      colocar(actual);
    };
    map.on('moveend', alTerminarDeMover);
    return () => {
      map.off('moveend', alTerminarDeMover);
    };
    // Sólo importa qué camión está elegido: `selectedTruck` cambia cada latido.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  /* Al cambiar el tamaño de la ventana, la tarjeta vuelve a entrar. */
  useEffect(() => {
    const alRedimensionar = () => {
      const el = caja.current;
      if (!el) return;
      const caja_ = el.getBoundingClientRect();
      setPosicion(limitar({ x: caja_.left, y: caja_.top }, caja_.width, caja_.height));
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
    movida.current = true;
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
