# Roadmap — Mes 1: Fundamentos del MVP de Geolocalización

**Objetivo del mes:** Tener el flujo completo (GPS → servidor → mapa) funcionando con datos simulados o de banco de pruebas, sin necesidad de instalarlo aún en un camión real.

**Supuesto de disponibilidad:** cada uno dedica entre 4 y 6 horas semanales al proyecto (los 3 tienen 40hs/semana entre trabajo y cursada). Este plan está pensado para ese ritmo — no para un sprint intensivo.

**Reunión semanal:** 1 encuentro corto (30-45 min) por semana, fin de semana o el día que mejor les quede a los 3, para sincronizar avances y destrabar dudas. Es el único punto obligatorio de coordinación.

---

## Semana 1 — Investigación y setup de entorno

| Responsable | Actividad | Horas est. |
|---|---|---|
| Ing. Electrónico | Elegir módulo GPS (NEO-6M o similar) y microcontrolador (ESP32 recomendado). Pedir/conseguir el hardware si no lo tienen. | 3h |
| Ing. Electrónico | Instalar entorno de desarrollo (Arduino IDE o PlatformIO) y correr un primer sketch de prueba (blink, sin GPS todavía) | 2h |
| Lic. Cs. Computación | Definir arquitectura mínima: lenguaje/framework del backend (ej. Node.js + Express, o Python + FastAPI) y motor de base de datos (Postgres) | 2h |
| Lic. Cs. Computación | Levantar un servidor local básico ("hello world" de API) y repo en Git compartido | 3h |
| Ing. Industrial | Redactar documento de alcance del MVP: qué se entrega este mes, qué queda para después (2do mes) | 3h |
| Ing. Industrial | Armar plantilla de seguimiento del proyecto (Trello/Notion/Excel — lo que usen para las próximas semanas) | 2h |

**Entregable de la semana:** repo creado, entorno de cada uno andando, documento de alcance compartido.

---

## Semana 2 — Primeros datos, aunque sea simulados

| Responsable | Actividad | Horas est. |
|---|---|---|
| Ing. Electrónico | Conectar el módulo GPS físicamente al microcontrolador y leer datos crudos por consola (NMEA) | 4h |
| Ing. Electrónico | Parsear los datos NMEA a lat/long legible (librería TinyGPS++ o similar) | 3h |
| Lic. Cs. Computación | Crear el endpoint `POST /posicion` que reciba `{device_id, lat, lng, timestamp}` y lo guarde en la base de datos | 4h |
| Lic. Cs. Computación | Probar el endpoint con datos falsos (Postman o curl) para validar que guarda bien | 2h |
| Ing. Industrial | Investigar 2-3 opciones de SIM/plan de datos IoT en Argentina (costos, cobertura) para cuando haya que conectar el hardware a internet | 3h |
| Ing. Industrial | Preparar un mini-documento con lo investigado sobre competencia (precios, features) para referencia del equipo | 2h |

**Entregable de la semana:** GPS leyendo posición real en banco de pruebas; backend guardando datos de prueba en la base.

---

## Semana 3 — Conectar las dos puntas

| Responsable | Actividad | Horas est. |
|---|---|---|
| Ing. Electrónico | Agregar módulo de comunicación (WiFi del ESP32 como primer paso, antes de sumar GSM) para enviar los datos del GPS al servidor | 5h |
| Ing. Electrónico | Probar el envío real: el dispositivo manda su posición cada X segundos al endpoint del compañero | 3h |
| Lic. Cs. Computación | Armar un mapa web simple (Leaflet o Google Maps API) que lea de la base de datos y muestre el último punto recibido | 5h |
| Lic. Cs. Computación | Ajustar el backend según lo que vaya fallando en la integración con el hardware | 2h |
| Ing. Industrial | Coordinar la prueba de integración de la semana (juntar a los otros dos, aunque sea por videollamada, para el primer test end-to-end) | 2h |
| Ing. Industrial | Empezar a bocetar el pricing preliminar (costo de hardware + SIM + margen) con los datos investigados la semana anterior | 3h |

**Entregable de la semana:** primer dato real viajando de punta a punta — del GPS al mapa web, aunque sea desde una notebook en un escritorio.

---

## Semana 4 — Consolidar y mostrar avance

| Responsable | Actividad | Horas est. |
|---|---|---|
| Ing. Electrónico | Ajustar la frecuencia de envío de datos y probar estabilidad (dejar el dispositivo mandando datos por varias horas seguidas, ver si se cae) | 4h |
| Ing. Electrónico | Documentar el circuito armado hasta ahora (fotos, diagrama simple) para referencia futura | 2h |
| Lic. Cs. Computación | Mejorar el mapa: mostrar historial de los últimos puntos (no solo el último), aunque sea una lista simple | 4h |
| Lic. Cs. Computación | Deploy básico del backend en un servidor accesible (Render, Railway, o similar de capa gratuita) para no depender de correr todo en local | 3h |
| Ing. Industrial | Preparar una mini-demo (2-3 slides o un video corto) de lo logrado este mes, para eventualmente mostrarle a la empresa el avance | 3h |
| Ing. Industrial | Revisar con el equipo qué quedó pendiente y armar el plan preliminar del mes 2 (recién ahí, no antes) | 2h |

**Entregable de la semana:** sistema funcionando de punta a punta accesible desde internet (no solo en red local), con historial básico visible en el mapa.

---

## Notas importantes

- **No es grave si algo se corre de semana.** El plan asume 4-6hs semanales reales, que con imprevistos de trabajo/facultad a veces son 2 o 3. Está pensado para absorber eso sin que se sienta como atraso grave.
- **La integración (semana 3) es el punto crítico.** Si el hardware y el backend no logran "hablarse" ese momento, es mejor destrabarlo juntos en la reunión semanal antes de seguir sumando features.
- **Recién al final de la semana 4** conviene planear el mes 2 (ahí probablemente entre: GSM/SIM real en vez de WiFi, alertas básicas, geocercas — lo que ya charlamos antes).
