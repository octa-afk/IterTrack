from fastapi import FastAPI
from fastapi.responses import FileResponse
from source.services.tracking import router as tracking_router
from source.services.auth import router as auth_router
 
app = FastAPI()
app.include_router(tracking_router)
app.include_router(auth_router)
 
 
@app.get("/")
async def root():
    return FileResponse("source/static/login.html")

@app.get("/map")
def view_map():
    return FileResponse("source/static/map.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("source/static/imagen-removebg-preview.png")

@app.get("/logo", include_in_schema=False)
def logo():
    return FileResponse("source/static/Itertrack_logo.png")
