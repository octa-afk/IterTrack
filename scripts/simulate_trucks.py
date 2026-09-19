import requests
import random
import time

BASE_URL = "http://127.0.0.1:8000/trucks"
lat = -31.4166867
long = -64.1834193

def registrar_camion(truck_id: int, lat: float, long: float, plate: str):
    response = requests.post(BASE_URL, json={
        "truck": {"id": truck_id, "plate": plate},
        "location": {"lat": lat, "long": long}
    })
    print(response.status_code, response.json())

def mover_aleatoriamente(lat: float, long: float, paso: float = 0.001):
    lat, long = lat + random.uniform(-paso, +paso), long + random.uniform(-paso, +paso) 
    return lat, long

def actualizar_ubicacion(truck_id: int, lat: float, long: float):
    response = requests.put(f"{BASE_URL}/{truck_id}/location", json={
        "lat": lat,
        "long": long
    })
    print(response.status_code, response.json())

if __name__ == "__main__":
    truck_id = 1
    lat, long = -31.4166867, -64.1834193 
    plate = "ABC123"
    registrar_camion(truck_id, lat, long, plate)

    while True:
        lat, long = mover_aleatoriamente(lat, long)
        actualizar_ubicacion(truck_id, lat, long)
        time.sleep(2)