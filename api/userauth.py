from nicegui import app
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from logic.credentials_management import CheckCredentialsResponseModel, CreateUserResponseModel, NullUserFieldError, UsernameExistsError, WrongCredentialsError, check_credentials_corelogic, create_user_corelogic

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