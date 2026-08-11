from fastapi import FastAPI
from source.services.tracking import router as tracking_router
 
app = FastAPI()
 
app.include_router(tracking_router)
 
 
@app.get("/")
async def root():
    return "Itertrack in the house 😎💯🚚"
