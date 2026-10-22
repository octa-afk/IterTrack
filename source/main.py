from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from source.services.tracking import router as tracking_router
from source.services.auth import router as auth_router
from source.services.devices import router as devices_router
 
app = FastAPI()
app.include_router(tracking_router)
app.include_router(auth_router)
app.include_router(devices_router)

# Only the asset directories are exposed; the HTML routes stay as explicit
# FileResponse endpoints so the source pages are never served as raw files.
app.mount("/static/css", StaticFiles(directory="source/static/css"), name="css")
app.mount("/static/js", StaticFiles(directory="source/static/js"), name="js")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return FileResponse("source/static/login.html")

@app.get("/map")
def view_map():
    return FileResponse("source/static/map.html")

@app.get("/register")
def view_register():
    return FileResponse("source/static/register.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("source/static/isologo.png")
