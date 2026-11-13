# IterTrack — Plan Etapa 1: GPS por LTE desde el auto

**Objetivo:** que la placa LilyGO (ESP32-WROVER-E + A7670SA-FASE con GNSS), alimentada desde el OBD-II del auto, mande su posición GPS al servidor del compañero cada pocos segundos, por **HTTP**. Sin CAN por ahora.

**Roles:** arquitectura e ideas → Juani · coordinación, firmware y mentoría → Claude · servidor → compañero de Computación.

**Pendientes sueltos:** ver `Pendientes.md`.

---

## 📅 Cronograma hasta el 28/11

| Semana | Estudio | Práctica |
|---|---|---|
| **13–20 nov** | Guía y esquemático de la LilyGO, comandos AT básicos | Instalar el entorno, correr `ATdebug` y `GPS_BuiltIn` (primer *fix*, sin chip). Comprar los materiales de alimentación |
| **21–28 nov** | Notas de aplicación de HTTP y GNSS del A76XX | Firmware: GPS → JSON → POST **por WiFi** a un servidor de prueba. Contrato de API listo. Si llega el chip: registro en la red |

**Meta para el 28/11:** GPS dando posición, datos saliendo por HTTP vía WiFi, contrato de API acordado y materiales comprados.
**El 28/11:** cambiar WiFi por LTE, conectarse al servidor del compañero → primer dato real en su base de datos.

---

## Fase 0 — Preparación y estudio
- [x] Confirmar el modelo de la LilyGO: **A7670SA-FASE, con GNSS** ✅
- [x] Juntar la documentación (carpeta `Datasheets`, ver `LEEME.md`) ✅
- [ ] Conseguir un **chip SIM con datos** y averiguar su **APN**. *(próximas semanas)*
- [ ] Probar el chip en un celular: que tenga datos y **sin PIN** (o anotar el PIN).
- [ ] Antenas: LTE y GPS conectadas. **Nunca encender el módem sin la antena LTE.**
- [ ] Entorno: driver CH9102 + **Arduino IDE** + core ESP32 + librerías de la carpeta `lib` de LilyGO (TinyGSM fork; no actualizar).
- [ ] Estudio guiado del A7670 y el ESP32 (preguntas y respuestas).
- [ ] Contrato de API con el compañero: **URL**, **POST**, **formato JSON**, respuestas y errores.

## Fase 1 — En la mesa, con USB
- [ ] "Hola mundo" del ESP32 (LED o Serial).
- [ ] Puente serie ESP32 ↔ módem para mandar comandos AT a mano: `AT`, `AT+CPIN?`, `AT+CSQ`, `AT+CEREG?`, `AT+COPS?`.
- [ ] GPS: encenderlo y conseguir un *fix* al aire libre o junto a una ventana (el primero puede tardar 1–5 min). *Se puede hacer sin chip.*

## Fase 2 — Envío de datos por HTTP
- [ ] **Primero por WiFi** (sin chip): GPS → JSON → POST a un servidor de prueba (PC local o webhook.site).
- [ ] Con el chip: configurar el APN, abrir la conexión de datos y obtener una IP.
- [ ] Cambiar el transporte de WiFi a LTE y mandar el POST al servidor del compañero.
- [ ] Firmware v0.1: GPS → JSON → POST cada N segundos, con reintentos y reconexión.

Formato propuesto (a acordar):
```json
{"id":"itt-001","ts":1731456000,"lat":-34.6037,"lon":-58.3816,"spd":42.5,"sats":9,"fix":true}
```

## Fase 3 — Alimentación desde el OBD-II
- [ ] Medir con el multímetro: **pin 16 = +12 V permanente**, **pines 4/5 = masa**. Medir con el motor apagado y en marcha.
- [ ] Armar la alimentación: **ficha OBD macho → fusible → diodo contra polaridad inversa → TVS → buck 12 V→5 V (≥3 A) → filtro LC → USB/5 V de la placa**.
- [ ] Probar en la mesa con una fuente de 12–14 V antes de enchufarlo al auto.
- [ ] Experimento: C/N0 del GPS con powerbank vs. con buck (ruido de conmutación).
- [ ] ⚠️ El pin 16 tiene tensión aunque el auto esté apagado: en esta etapa, **desenchufar al bajar del auto**.

## Fase 4 — Prueba en el auto
- [ ] Recorrido corto con la notebook conectada para ver los logs.
- [ ] Verificar: tiempo hasta el fix, cortes de señal, reconexión, consumo y temperatura.
- [ ] Guardar los datos en memoria (PSRAM o flash) mientras no hay señal y mandarlos después.

## Después (Etapa 2 en adelante)
- Módulo CAN en el auto: OBD-II por CAN (ISO 15765, consulta de PIDs, normalmente a 500 kbps). Primero en modo *listen-only*.
- Camiones: J1939 (broadcast, 250/500 kbps) y J1708.
- Batería de respaldo, corte por baja tensión, gabinete y PCB propia.
