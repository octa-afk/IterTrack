import requests
import random
import time

BASE_URL = "http://127.0.0.1:8000/trucks"

# TODO: definí un punto de partida (lat, long) — podés usar coordenadas
# reales de la zona donde opera la empresa como centro del recorrido

def registrar_camion(truck_id: int, lat: float, long: float):
    # TODO: hacé el POST a BASE_URL con el body {"truck": {...}, "location": {...}}
    # fijate en tracking.py que add_truck espera "truck" y "location" como
    # parámetros separados en el body (no anidados en un mismo objeto)
    pass

def mover_aleatoriamente(lat: float, long: float, paso: float = 0.001):
    # TODO: sumale a lat y long un delta random entre -paso y +paso
    # random.uniform(-paso, paso) te sirve para esto
    pass

def actualizar_ubicacion(truck_id: int, lat: float, long: float):
    # TODO: hacé el PUT a f"{BASE_URL}/{truck_id}/location"
    pass

if __name__ == "__main__":
    truck_id = 1
    lat, long = -31.4201, -64.1888  # TODO: ajustá el punto de partida

    registrar_camion(truck_id, lat, long)

    while True:
        lat, long = mover_aleatoriamente(lat, long)
        actualizar_ubicacion(truck_id, lat, long)
        time.sleep(2)  # TODO: ajustá el intervalo que tenga sentido
