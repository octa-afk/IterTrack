from fastapi import FastAPI
from fastapi.responses import FileResponse
from source.services.tracking import router as tracking_router
from source.services.auth import router as auth_router
 
app = FastAPI()
app.include_router(tracking_router)
app.include_router(auth_router)
 
 
@app.get("/")
async def root():
    return "Itertrack in the house 😎💯🚚"

@app.get("/map")
def view_map():
    return FileResponse("source/static/map.html")
