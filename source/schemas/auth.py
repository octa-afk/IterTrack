from pydantic import BaseModel

class User(BaseModel):
    username: str
    email: str
    full_name: str
    hashed_password: str
    disabled: bool