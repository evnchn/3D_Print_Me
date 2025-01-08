from nicegui import app

from pydantic import BaseModel

from auth_lib.security_definitions import priviledged_users, passwords
from auth_lib.auth import deserialize_str_to_bytes, hash_new_password, is_correct_password, serialize_bytes_to_str

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
        return {"detail": "Credentials are correct"}
    raise WrongCredentialsError("Wrong username or password")
