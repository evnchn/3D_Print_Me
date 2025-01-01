from typing import Annotated
from fastapi import Depends
from nicegui import app

from logic.credentials_management import get_user_from_jwt_token

@app.get("/user/me/")
async def read_my_name(current_user: Annotated[str, Depends(get_user_from_jwt_token)]):
    return current_user