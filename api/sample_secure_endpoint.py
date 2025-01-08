from typing import Annotated
from fastapi import Depends
from nicegui import app

from auth_lib.credentials_management_api import get_user_from_jwt_token

@app.get("/user/me/")
async def read_my_name(current_user: Annotated[str, Depends(get_user_from_jwt_token)]):
    return current_user

@app.get("/user/me/am_i_admin/")
async def read_my_name(current_user: Annotated[str, Depends(get_user_from_jwt_token)]):
    # check current_user against the database at app.storage.general
    return app.storage.general.get("user_pw", {}).get(current_user, {}).get("admin", False)