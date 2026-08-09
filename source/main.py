
from fastapi import FastAPI
from app.services.tracking import router as tracking_router
 
app = FastAPI()
 
app.include_router(tracking_router)
 
 
@app.get("/")
async def root():
    return "Itertrack in the house 😎💯🚚"
