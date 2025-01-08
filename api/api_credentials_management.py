from nicegui import app

from fastapi import Depends, HTTPException
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from auth_lib.credentials_management import CheckCredentialsResponseModel, NullUserFieldError, WrongCredentialsError, check_credentials_corelogic

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class CheckTokenResponseModel(BaseModel):
    token: str

class InvalidTokenError(Exception):
    pass

class MalformedTokenError(Exception):
    pass

class ExpiredTokenError(Exception):
    pass

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_from_jwt_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # check the credentials via check_credentials_corelogic
    response = CheckCredentialsResponseModel(username=form_data.username, password=form_data.password)
    try:
        result = check_credentials_corelogic(response)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    except NullUserFieldError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WrongCredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_admin_user_from_jwt_token(current_user: Annotated[str, Depends(get_user_from_jwt_token)]) -> str:
    if app.storage.general.get("user_pw", {}).get(current_user, {}).get("admin", False):
        return current_user
    raise HTTPException(status_code=401, detail="Not enough priviledges")