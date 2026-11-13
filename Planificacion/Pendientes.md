# IterTrack — Lista de pendientes ("to do")

Lista viva de cosas que van surgiendo en las charlas. Claude la actualiza a medida que aparecen temas nuevos o se completan.
Prioridad: 🔴 bloquea la etapa actual · 🟡 esta etapa · 🟢 más adelante

_Última actualización: 13/11/2026_

## 🛒 Compras
- [ ] 🔴 Chip SIM con datos (Personal / Claro / Movistar, prepago alcanza) + averiguar APN
- [ ] 🟡 Ficha OBD-II macho con cable
- [ ] 🟡 Buck 12 V → 5 V, ≥3 A, de buena calidad, idealmente con conmutación ≥1 MHz
- [ ] 🟡 Portafusible + fusible (≈2–3 A)
- [ ] 🟡 Diodo para protección contra polaridad inversa (Schottky, ej. SS34 / 1N5822)
- [ ] 🟡 TVS para los picos del auto (*load dump*, arranque); el modelo exacto se define junto con el buck
- [ ] 🟡 Ferrita o inductor + capacitores para un filtro LC a la salida del buck
- [ ] 🟡 Batería 18650 Li-ion 4,2 V (**no LiFePO4**: la LilyGO no la soporta)

## 💻 Entorno y software
- [ ] 🔴 Instalar el driver CH9102, el Arduino IDE y el core del ESP32
- [ ] 🔴 Copiar las librerías de la carpeta `lib` del repo de LilyGO (TinyGSM fork) y **no actualizarlas** desde el IDE
- [ ] 🟡 Ordenar el repo git (github.com/octa-afk/IterTrack): commitear el borrado del proyecto PlatformIO viejo `Iter-Hard/`, decidir si `Datasheets/` va al repo (pesa ~13 MB) y armar la estructura de carpetas del firmware
- [ ] 🟡 Firmware en capas: lógica GPS/JSON separada del transporte (primero WiFi, después LTE) — punto de partida: `PruebasHttp/PrimerasPruebas_Http`
- [ ] 🟡 Bajar a mano el *ESP32 Series Datasheet* y el *Technical Reference Manual* (links en `Datasheets/LEEME.md`)

## 🤝 Coordinación del equipo
- [ ] 🟡 Contrato de API con el compañero de Computación: URL, POST, campos del JSON, respuestas y errores (borrador: Claude)
- [ ] 🟡 Definir el rol del compañero de Industrial (ideas: relevar la flota —marcas, años, J1939 o no—, comparar planes de datos IoT, costo por unidad)

## 🔬 Experimentos para hacer
- [ ] 🟡 Ruido del buck sobre el GPS: comparar C/N0 de los satélites con powerbank vs. buck, mismo lugar
- [ ] 🟢 Medir el ripple del buck con el osciloscopio (límite de BW 20 MHz, masa corta con resorte)

## 🚗 Instalación en el auto
- [ ] 🟡 Medir el pin 16 (+12 V permanente) y los pines 4/5 (masa) con motor apagado y en marcha
- [ ] 🟡 Probar la cadena de alimentación con una fuente de banco antes del auto
- [ ] 🟡 Antena GPS lejos del buck y de sus cables, mirando al cielo
- [ ] 🟡 Desenchufar al bajar del auto (el pin 16 siempre tiene tensión) hasta tener corte por baja tensión

## 🔌 Módulo CAN (Etapa 2)
- [ ] 🟢 Adaptar niveles: SO e INT salen a 5 V → divisor resistivo o alimentar el MCP2515 a 3,3 V (cortando la pista)
- [ ] 🟢 Verificar el cristal del módulo (suele ser 8 MHz) y configurarlo en la librería
- [ ] 🟢 Quitar el jumper de terminación de 120 Ω al conectarlo a un vehículo
- [ ] 🟢 Primeras pruebas en modo *listen-only*

## 🧩 Para la PCB propia (v2)
- [ ] 🟢 Reemplazar MCP2515 + TJA1050 por el TWAI del ESP32 + SN65HVD230 (3,3 V)
- [ ] 🟢 Batería LiFePO4 con su propio cargador
- [ ] 🟢 Corte por baja tensión y modo sleep para no descargar la batería del vehículo
- [ ] 🟢 Conversión de nivel 1,8 V ↔ 3,3 V entre el módem y el ESP32
- [ ] 🟢 Buck con filtrado y layout cuidado (lazos cortos, plano de masa, lejos de la antena GPS)

## ✅ Hecho
- [x] Revisar los datasheets iniciales
- [x] Confirmar el modelo: LilyGO T-A7670SA-FASE (GPS integrado, bandas de Argentina)
- [x] Juntar la documentación de módem, placa y librerías en la carpeta Datasheets
- [x] Repositorio git del proyecto creado (github.com/octa-afk/IterTrack)
