from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
        username: str
        fullname: str
        email: str
        disabled: bool

