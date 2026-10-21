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
app.mount("/assets", StaticFiles(directory="source/static/app/assets"), name="react-assets")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return FileResponse("source/static/app/index.html")

@app.get("/map")
def view_map():
    return FileResponse("source/static/app/index.html")

@app.get("/register")
def view_register():
    return FileResponse("source/static/app/index.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("source/static/isologo.png")
