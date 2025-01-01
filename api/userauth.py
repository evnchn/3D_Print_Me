from fastapi import Depends
from nicegui import app
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

import time
from logic.credentials_management import CheckCredentialsResponseModel, CheckTokenResponseModel, CreateUserResponseModel, ExpiredTokenError, InvalidTokenError, MalformedTokenError, NullUserFieldError, UsernameExistsError, WrongCredentialsError, check_credentials_corelogic, check_token_corelogic, create_user_corelogic

@app.post("/api/create_user", responses={
    200: {"description": "User created successfully", "content": {"application/json": {"example": {"detail": "User created successfully"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Username or password cannot be empty"}}}},
    401: {"description": "Unauthorized", "content": {"application/json": {"example": {"detail": "Wrong master username or password"}}}},
    409: {"description": "Conflict", "content": {"application/json": {"example": {"detail": "Username already exists"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
})
def create_user(response: CreateUserResponseModel):
    try:
        if create_user_corelogic(response):
            return {"detail": "User created successfully"}, 200
    except NullUserFieldError as e:
        return {"detail": str(e)}, 400
    except WrongCredentialsError as e:
        return {"detail": str(e)}, 401
    except UsernameExistsError as e:
        return {"detail": str(e)}, 409
    except Exception as e:
        return {"detail": str(e)}, 500

@app.post("/api/check_credentials", responses={
    200: {"description": "Credentials are correct", "content": {"application/json": {"example": {"detail": "Credentials are correct"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Username or password cannot be empty"}}}},
    401: {"description": "Unauthorized", "content": {"application/json": {"example": {"detail": "Wrong username or password"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
})
def check_credentials(response: CheckCredentialsResponseModel):
    try:
        return check_credentials_corelogic(response)
    except NullUserFieldError as e:
        return {"detail": str(e)}, 400
    except WrongCredentialsError as e:
        return {"detail": str(e)}, 401
    except Exception as e:
        return {"detail": str(e)}, 500
    
# similar to above, /api/mint_token and /api/verify_token, token stored in app.storage.general["api_tokens"] key token value {"username":username, "__time__": int(time.time())}, token from uuid_handling.py generate_prefixed_uuid apitoken prefix
from utils.uuid_handling import generate_prefixed_uuid, match_prefixed_uuid

@app.post("/api/mint_token", responses={
    200: {"description": "Token minted successfully", "content": {"application/json": {"example": {"detail": "Token minted successfully"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Username or password cannot be empty"}}}},
    401: {"description": "Unauthorized", "content": {"application/json": {"example": {"detail": "Wrong username or password"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
})
def mint_token(response: CheckCredentialsResponseModel):
    try:
        result = check_credentials_corelogic(response)
        # auth is successful if the code reaches here
        token = generate_prefixed_uuid("apitoken")
        # assert api_tokens key exists
        if "api_tokens" not in app.storage.general:
            app.storage.general["api_tokens"] = {}
        app.storage.general["api_tokens"][token] = {"username": response.username, "__time__": int(time.time())}    
    except NullUserFieldError as e:
        return {"detail": str(e)}, 400
    except WrongCredentialsError as e:
        return {"detail": str(e)}, 401
    except Exception as e:
        return {"detail": str(e)}, 500
    
# verify_token to use check_token_corelogic from logic/credentials_management.py
@app.post("/api/verify_token", responses={
    200: {"description": "Token is valid", "content": {"application/json": {"example": {"detail": "Token is valid"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Token format is invalid"}}}},
    401: {"description": "Unauthorized", "content": {"application/json": {"example": {"detail": "Token is invalid"}}}},
    403: {"description": "Forbidden", "content": {"application/json": {"example": {"detail": "Token is expired"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}    
})
def verify_token(response: CheckTokenResponseModel):
    try:
        if check_token_corelogic(response):
            username = app.storage.general["api_tokens"][response.token]["username"]
            return {"detail": "Token is valid", "username": username, "admin": app.storage.general["user_pw"][username]["admin"]}, 200
    except MalformedTokenError as e:
        return {"detail": str(e)}, 400
    except InvalidTokenError as e:
        return {"detail": str(e)}, 401
    except ExpiredTokenError as e:
        return {"detail": str(e)}, 403
    except Exception as e:
        return {"detail": str(e)}, 500
    
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # check the token via verify_token
    response = CheckTokenResponseModel(token=token)
    try:
        if check_token_corelogic(response):
            return response
    except MalformedTokenError as e:
        return {"detail": str(e)}, 400
    except InvalidTokenError as e:
        return {"detail": str(e)}, 401
    except ExpiredTokenError as e:
        return {"detail": str(e)}, 403
    except Exception as e:
        return {"detail": str(e)}, 500