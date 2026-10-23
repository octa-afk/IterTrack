from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from source.services.auth import router as auth_router
from source.services.devices import router as devices_router
from source.services.organizations import router as organizations_router
from source.services.tracking import org_router
from source.services.tracking import router as tracking_router

# Built React app (Vite). Build it with: npm --prefix frontend run build
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FAVICON = Path(__file__).resolve().parent / "static" / "isologo.png"

app = FastAPI()
app.include_router(tracking_router)
app.include_router(org_router)
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(organizations_router)

# Only the hashed build assets are exposed as files; every route is answered
# with index.html so React Router owns the client-side routing.
app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIST / "assets", check_dir=False),
    name="assets",
)


def _index() -> FileResponse:
    target = FRONTEND_DIST / "index.html"
    if not target.is_file():
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found. Run: npm --prefix frontend run build",
        )
    return FileResponse(target)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return _index()


@app.get("/map")
def view_map():
    return _index()


@app.get("/register")
def view_register():
    return _index()


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(FAVICON)
