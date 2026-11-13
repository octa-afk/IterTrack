# IterTrack — Documentación para estudiar (Etapa 1)

Qué hay en esta carpeta y en qué orden conviene leerlo.

## 1. Placa LilyGO  (`Placa LilyGO/`)
Empezá por acá: describe la placa que **tenés en la mano**.
- **T-A7670X_Guia_rapida_y_pines.md**: modelos, pines del ESP32 usados por el módem, alimentación, configuración del Arduino IDE. Tu placa con GPS integrado es la **A7670SA-FASE** (SKU Q335).
- **Esquematico_T-A7670X-V1.4.pdf**: el circuito real de la placa (fuente del módem, conversión de niveles, SIM, cargador). Es la referencia para la PCB propia.
- **Bugs_conocidos_firmware_SIMCom.md**: problemas conocidos del firmware del módem.

## 2. Módulo SIMCom A7670  (`Modulo SIM-GPS/`)
- **A7670 Series Hardware Design_V1.00.pdf** *(ya lo tenías)*: hardware del módulo.
- **A76XX_Series_AT_Command_Manual_V1.12.pdf**: el "diccionario" de comandos AT. No se lee de corrido: se consulta.
- **GNSS Application Note**: cómo prender el GPS y leer la posición (`AT+CGNSSPWR`, `AT+CGNSSINFO`…).
- **HTTP(S) Application Note**: cómo hacer GET/POST con los comandos HTTP del módem (`AT+HTTPINIT`…).
- **TCPIP Application Note**: conexión de datos y sockets (lo que hay "debajo" de HTTP).
- **UART Application Note**: comunicación serie ESP32 ↔ módem.
- **Sleep Mode Application Note**: bajo consumo (para más adelante).
- **Especificaciones de antenas LTE y GPS**.

## 3. Microcontrolador  (`uControlador/`)
- **esp32-wrover-e_esp32-wrover-ie_datasheet_en.pdf** *(ya lo tenías)*.
- ⚠️ Faltan dos documentos que no pude descargar automáticamente (bajalos a mano desde la web de Espressif):
  - *ESP32 Series Datasheet*: https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf
  - *ESP32 Technical Reference Manual* (periféricos en detalle: UART, TWAI, etc.): https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf

## 4. Librerías  (`Librerias/`)
- **TinyGSM/**: librería para manejar el módem desde Arduino sin escribir los AT a mano. **Usar el fork de LilyGO/lewisxhe** (viene en la carpeta `lib` del repo de LilyGO), no la versión oficial: la oficial no soporta bien el A7670.
- **ArduinoHttpClient/**: cliente HTTP que funciona sobre la conexión de TinyGSM.
- **ESP32 Arduino Core/**: documentación oficial de las APIs del ESP32 en Arduino. Para esta etapa: `serial.md` (clave), `gpio.md`, `timer.md`, `preferences.md` (guardar configuración), `deepsleep.md`, `adc.md` (batería), `spi.md` (para el MCP2515 más adelante).
- **Ejemplos LilyGO/**: ejemplos oficiales que vamos a estudiar y adaptar, en este orden:
  1. `ATdebug`: puente serie para mandar comandos AT a mano.
  2. `GPS_BuiltIn`: leer el GPS integrado.
  3. `Network`: registro en la red y conexión de datos.
  4. `HttpClient`: HTTP con TinyGSM + ArduinoHttpClient.
  5. `HttpsBuiltlnPost`: POST usando el cliente HTTP **interno del módem**.

## Notas importantes de la guía de LilyGO
- La entrada USB/VBUS tiene que dar **picos de al menos 2 A sin bajar de 5 V**, o la placa se apaga. Tenerlo en cuenta para el buck del OBD-II.
- La batería de la placa es **solo Li-ion/LiPo de 4,2 V (18650)**. **No usar LiFePO4** en esta placa.
- **GPIO12** habilita la alimentación del módem: tiene que estar en alto.
- No conectar nada en los pines GPIO4 (PWRKEY) ni GPIO5 (RESET) del header.
- Si se pone una tarjeta SD, hay que sacarla para subir código (usa el GPIO2).
- Al abrir el Arduino IDE, **no actualizar las librerías** que copiaste del repo de LilyGO.

Fuente: https://github.com/Xinyuan-LilyGO/LilyGO-T-A76XX
