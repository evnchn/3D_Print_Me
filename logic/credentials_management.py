from datetime import datetime, timedelta, timezone
import time
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from nicegui import app

from pydantic import BaseModel

from utils.security_definitions import priviledged_users, passwords
from utils.auth import deserialize_str_to_bytes, hash_new_password, is_correct_password, serialize_bytes_to_str
from utils.uuid_handling import match_prefixed_uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT handling
import jwt

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

# error types for the login page, wrong username or password, or username already exists
class WrongCredentialsError(Exception):
    pass

class UsernameExistsError(Exception):
    pass

class NullUserFieldError(Exception):
    pass

# pydantic models for the login page
class CreateUserResponseModel(BaseModel):
    master_username: str
    master_password: str
    username: str
    password: str

class CheckCredentialsResponseModel(BaseModel):
    username: str
    password: str

def create_user_corelogic(response: CreateUserResponseModel) -> bool:
    if not response.username or not response.password:
        raise NullUserFieldError("Username or password cannot be empty")

    if passwords.get(response.master_username) == response.master_password:
        if 'user_pw' not in app.storage.general:
            app.storage.general['user_pw'] = {}

        if response.username in app.storage.general['user_pw']:
            raise UsernameExistsError("Username already exists")

        is_admin = response.master_username in priviledged_users
        salt, pw_hash = hash_new_password(response.password)
        app.storage.general['user_pw'][response.username] = {'salt': serialize_bytes_to_str(salt), 'pw_hash': serialize_bytes_to_str(pw_hash), 'admin': is_admin}
        app.storage.user.update({'username': response.username, 'authenticated': True})
        return True
    raise WrongCredentialsError("Wrong master username or password")

def check_credentials_corelogic(response: CheckCredentialsResponseModel):
    if not response.username or not response.password:
        raise NullUserFieldError("Username or password cannot be empty")

    user_pw = app.storage.general.get('user_pw', {}).get(response.username)
    if not user_pw:
        raise WrongCredentialsError("Wrong username or password")

    salt = deserialize_str_to_bytes(user_pw['salt'])
    pw_hash = deserialize_str_to_bytes(user_pw['pw_hash'])
    if is_correct_password(salt, pw_hash, response.password):
        return {"detail": "Credentials are correct"}, 200
    raise WrongCredentialsError("Wrong username or password")

class CheckTokenResponseModel(BaseModel):
    token: str

class InvalidTokenError(Exception):
    pass

class MalformedTokenError(Exception):
    pass

class ExpiredTokenError(Exception):
    pass

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
    
# import pyjwt
