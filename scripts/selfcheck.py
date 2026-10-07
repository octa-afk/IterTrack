"""Autoverificación sin dependencias extra:
- Lógica JS de source/static/map.html ejecutada con node (ya instalado).
- API FastAPI con el TestClient interno + httpx (ya instalados), sin abrir puertos.
Uso: env/bin/python scripts/selfcheck.py
"""
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = []
FAIL = []


def check(nombre, ok, detalle=""):
    (PASS if ok else FAIL).append(nombre)
    marca = "OK " if ok else "FAIL"
    print(f"[{marca}] {nombre}" + (f"  ({detalle})" if detalle else ""))


# ---------- 1) Lógica JS real extraída de map.html, ejecutada con node ----------
html = (ROOT / "source/static/map.html").read_text(encoding="utf-8")
bloque_js = re.search(r"<script>(.*?)</script>\s*</body>", html, re.S).group(1)

# Extraer las funciones puras por nombre (sin DOM ni Leaflet)
def extraer_funcion(src, nombre):
    i = src.find(f"function {nombre}(")
    if i < 0:
        return ""
    j = src.find("{", i)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    return ""

fns = "\n\n".join(extraer_funcion(bloque_js, n) for n in
                  ("calcularRumbo", "calcularDistanciaMetros", "obtenerPuntoCardinal"))
assert "function calcularRumbo" in fns and "function obtenerPuntoCardinal" in fns

harness = fns + r"""
const checks = [];
// Rumbos conocidos
const rN = calcularRumbo(-31.0, -64.0, -30.5, -64.0);
const rE = calcularRumbo(-31.0, -64.0, -31.0, -63.5);
const rS = calcularRumbo(-31.0, -64.0, -31.5, -64.0);
const rO = calcularRumbo(-31.0, -64.0, -31.0, -64.5);
checks.push(["rumbo ~N ≈0°", Math.abs(rN - 0) < 1.5, rN.toFixed(2)]);
checks.push(["rumbo ~E ≈90°", Math.abs(rE - 90) < 1.5, rE.toFixed(2)]);
checks.push(["rumbo ~S ≈180°", Math.abs(rS - 180) < 1.5, rS.toFixed(2)]);
checks.push(["rumbo ~O ≈270°", Math.abs(rO - 270) < 1.5, rO.toFixed(2)]);
checks.push(["cardinales", obtenerPuntoCardinal(0) === 'N' && obtenerPuntoCardinal(90) === 'E'
             && obtenerPuntoCardinal(180) === 'S' && obtenerPuntoCardinal(270) === 'O' &&
             obtenerPuntoCardinal(45) === 'NE' && obtenerPuntoCardinal(315) === 'NO',
             [0,45,90,180,270,315].map(obtenerPuntoCardinal).join(',')]);
const d = calcularDistanciaMetros(-31.4167, -64.1834, -31.4267, -64.1834);
checks.push(["distancia ~1115m (0.01° lat)", Math.abs(d - 1112) < 40, d.toFixed(1) + 'm']);
console.log(JSON.stringify(checks));
"""
with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, dir="/tmp/opencode") as f:
    f.write(harness)
    tmp = f.name
try:
    out = subprocess.run(["node", tmp], capture_output=True, text=True, timeout=30)
    js_checks = json.loads(out.stdout.strip() or "[]")
    for nombre, ok, detalle in js_checks:
        check(f"[JS] {nombre}", bool(ok), str(detalle))
    if not js_checks:
        check("[JS] ejecución node", False, out.stderr.strip()[:120])
finally:
    Path(tmp).unlink(missing_ok=True)

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
