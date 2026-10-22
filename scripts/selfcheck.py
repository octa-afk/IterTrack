"""Autoverificación sin dependencias extra:
- Build del frontend React que sirve FastAPI.
- API FastAPI con el TestClient interno + httpx (ya instalados), sin abrir puertos.
Uso: env/bin/python scripts/selfcheck.py
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = []
FAIL = []


def check(nombre, ok, detalle=""):
    (PASS if ok else FAIL).append(nombre)
    marca = "OK " if ok else "FAIL"
    print(f"[{marca}] {nombre}" + (f"  ({detalle})" if detalle else ""))


# ---------- 1) Build del frontend servido por FastAPI ----------
dist_index = ROOT / "frontend" / "dist" / "index.html"
check(
    "[UI] build del frontend presente",
    dist_index.is_file(),
    "ejecutá: npm --prefix frontend run build",
)

# ---------- 2) API con TestClient en memoria ----------
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"fastapi.*")
warnings.filterwarnings("ignore", message=r".*httpx.*starlette.*")

from fastapi.testclient import TestClient
from source.main import app

client = TestClient(app)
username = f"selfcheck_{random.randint(10000, 99999)}"
email = f"{username}@test.com"

r = client.post("/auth/register", json={
    "username": username, "email": email, "full_name": "Self Check", "password": "secreto123"})
check("[API] registro de usuario (201)", r.status_code == 201, f"got {r.status_code}: {r.text[:80]}")

r = client.post("/auth/login", data={"username": username, "password": "secreto123"})
check("[API] login JWT (200)", r.status_code == 200 and "access_token" in r.json(), f"got {r.status_code}")
token = r.json().get("access_token", "")
auth = {"Authorization": f"Bearer {token}"}

truck_id = random.randint(100000, 999999)
r = client.post("/trucks", headers=auth, json={"truck": {"id": truck_id, "plate": f"SC{random.randint(100,999)}"},
                                               "location": {"lat": -31.4167, "long": -64.1834}})
check("[API] crear camión con token (200/201)", r.status_code in (200, 201), f"got {r.status_code}: {r.text[:80]}")

r = client.post("/trucks", json={"truck": {"id": truck_id + 1, "plate": "XX999"},
                                 "location": {"lat": 0, "long": 0}})
check("[API] crear camión sin token (401/403)", r.status_code in (401, 403), f"got {r.status_code}")

r = client.put(f"/trucks/{truck_id}/location", headers=auth, json={"lat": -31.4267, "long": -64.1834})
check("[API] update location (200)", r.status_code == 200, f"got {r.status_code}: {r.text[:80]}")

r = client.get(f"/trucks/{truck_id}/location")
check("[API] latest location refleja el update", r.status_code == 200 and abs(r.json().get("lat", 0) + 31.4267) < 1e-6, f"got {r.status_code} {r.text[:60]}")

r = client.get(f"/trucks/{truck_id}/iter")
check("[API] historial tiene 2 puntos", r.status_code == 200 and len(r.json()) == 2, f"got {len(r.json()) if r.status_code == 200 else r.status_code}")

r = client.put(f"/trucks/{truck_id}/location", headers=auth, json={"lat": 91.0, "long": 0})
check("[API] lat=91 rechazada (422)", r.status_code == 422, f"got {r.status_code}")

r = client.get("/trucks/999999999/location")
check("[API] camión inexistente (404)", r.status_code == 404, f"got {r.status_code}")

r = client.delete(f"/trucks/{truck_id}/iter", headers=auth)
check("[API] borrar historial (204)", r.status_code == 204, f"got {r.status_code}")
r = client.get(f"/trucks/{truck_id}/iter")
check("[API] historial vacío tras delete", r.status_code == 200 and r.json() == [], f"got {r.status_code} {r.text[:40]}")

# Limpieza de datos de test creados por esta corrida
try:
    from source.database.database import SessionLocal
    from source import models
    db = SessionLocal()
    db.query(models.TrackingPoint).filter(models.TrackingPoint.truck_id == truck_id).delete()
    db.query(models.Truck).filter(models.Truck.id == truck_id).delete()
    db.query(models.User).filter(models.User.username == username).delete()
    db.commit()
    db.close()
except Exception as e:
    print(f"(aviso) no se pudo limpiar la BD: {e}")

print("-" * 50)
print(f"{len(PASS)}/{len(PASS) + len(FAIL)} pruebas pasaron")
sys.exit(0 if not FAIL else 1)
