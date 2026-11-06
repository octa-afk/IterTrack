# Destinos y viajes tercerizados

Objetivo: modelar el envío real —un dador de carga manda destinos, la flota
asigna un camión— y resolver dirección → coordenada una sola vez, con caché y
cola de revisión manual. El proveedor de geocoding queda detrás de una interfaz
para poder pasar a Google en el lanzamiento sin tocar el dominio.
Rama: `feat/dashboard-original` · Entrega: commits por unidad · Tests: `make test`

## Specs

S1. Un **dador de carga** (`chargers`) pertenece a una organización y no es un
inquilino: no tiene login ni invitaciones.

S2. Un **viaje** (`trips`) une un dador, una fecha y opcionalmente un camión.
El chofer se guarda en el viaje, no en el camión: en tercerización el mismo
camión rota de chofer por envío.

S3. `external_ref` es idempotente por organización: el cliente reenvía lo que le
mandaron, y un mismo envío dos veces no puede duplicar viajes (responde `409`).

S4. Cada **destino** (`trip_stops`) guarda dirección, coordenada, procedencia
(`geo_source`), confianza y `needs_review`.

S5. La coordenada se resuelve **una sola vez, al importar**: caché por dirección
normalizada (`address_cache`, única por organización) y, si no está, una llamada
al geocoder. La dirección es texto para mostrar; la coordenada es la verdad.

S6. Si el geocoder no resuelve, el destino queda `needs_review=true` en la cola
de pendientes. Es parte del flujo, no un error: "Ruta 9 km 720" no geocodifica
con ningún proveedor.

S7. El pin manual resuelve el destino y **escribe la caché**: la próxima
importación de esa dirección no vuelve a preguntar.

S8. El geocoder es una interfaz (`Geocoder`) inyectada por `Depends`, con
implementación `none` por defecto. Los tests nunca salen a la red.

S9. Toda operación está acotada a la organización del usuario; crear o leer
recursos ajenos responde `404` para no filtrar existencia.

S10. La sección Rutas (`/viajes`) lista los viajes y ofrece a `org_admin` un
formulario con dador, camión disponible, destino y hora de salida.

S11. Un camión está disponible si está activo y no tiene viaje abierto; el radio
del depósito se evalúa más adelante, cuando exista detección de llegada.

## Tasks

| ID | Specs | Estado |
|----|-------|--------|
| T1 | S1-S4: modelos + migración | hecho |
| T2 | S5-S8: geocoding, caché, resolución | hecho |
| T3 | S9: endpoints y scoping | hecho |
| T4 | tests | hecho |

## Log

L1 (2026-10-24, textual): "nuestro cliente le terceriza camiones a otras
empresas que hacen envios de sus propios productos, por ejemplo tercerizan a
una empresa de colchones. entineod que la empresa de colchones le manda los
datos de destino a nuestro cliente y nuestro cliente nos pasa los destinos a
nosotros"

L2 (textual): "llegan con direcciones en general. se puede hacer con
openstreer? o habria que usar google maps ahi?"

L3 (textual): "para cuando el producto se lance quizas ahi ya sea necesario
google geocoding y usar google maps, quizas hay alguna opcion gratuita de
prueba. y si no pagaremos. pero necesito que el tema de direcciones y
cooerdenadas funcione perfectamente, es el qi del producto"

L4: decisión — el pipeline se construye agnóstico del proveedor. Nominatim
público no sirve en producción (1 req/s y 4 req/min para scripts periódicos,
según su política); Google queda para el lanzamiento y arrastra el mapa, porque
sus términos no permiten usar el geocoding fuera de un mapa de Google.

L5: primera tajada implementada (backend, sin UI). `chargers`, `trips`,
`trip_stops`, `address_cache` + migración `a5f65983b0d3`. Endpoints:
`GET/POST /chargers`, `GET/POST /trips`, `GET /trips/{id}`,
`PATCH /trips/{id}/stops/{stop_id}`, `GET /destinations/pending`.
Geocoder detrás de `Depends(get_geocoder)`; `none` por defecto.
Verificación: 10 tests nuevos (209 en total) y prueba contra Postgres real con
`GEOCODER_PROVIDER=none`: el destino sin coordenada queda pendiente, el pin
manual lo resuelve, y reimportar la misma dirección escrita distinto
("AV COLON 1234, cordoba") devuelve `geo_source: cache`. Los datos de la prueba
se borraron de la base.
Pendiente para la próxima: UI de viajes/destinos, asignación de camión desde la
pantalla, detección de llegada por radio (`arrived_at`/`departed_at` existen pero
nadie los escribe) y el import desde CSV/API del dador.

L6 (usuario, textual): "quizas nos conviene meter un apartado dentro de la
interfaz que nos permita usar uno de los camiones que están en el deposito para
crear un nuevo viaje. supongamos que el deposito estña en el centro de
cordoba, entonces la pagina te pediria un destino y un horario de salida"

L7: decisión del usuario — elegibilidad "sin viaje abierto" (el radio del
depósito queda para después). Implementado:
- `departure_at` reemplaza a `scheduled_for`; el schema exige zona horaria
  (422 si falta) para que un `datetime-local` no se lea como UTC.
- `depots` + `GET/POST /depots`; con un solo depósito el viaje lo toma solo.
- `GET /trips/available-trucks` (activo y sin viaje abierto). Verificado en la
  UI: con los camiones 1 y 2 tomados, el select sólo ofreció ABC123-03.
- Lecturas a `get_current_user`: sin eso el `member` de la demo veía 403 en
  todo. El formulario se oculta por `role`, que `/auth/me` sí devuelve (mi
  lectura inicial del tipo del frontend estaba desactualizada: el tipo no tenía
  `role` pero la API sí lo manda).
- Sección Rutas en `/viajes` (`/trips` es la API). `make test` 214 en verde.
Pendiente: resolver el pin desde la UI, detalle del viaje con destinos en el
mapa, y el alta de dador de carga desde la pantalla (hoy se crea por API).
