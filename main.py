# import os, load dotenv, get SECRET_KEY from .env
import os
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY_BYTES = SECRET_KEY.encode()

from nicegui import ui, app
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import hashlib
import hmac

import json
import base64

# HMAC SHA256
def hmac_sha256(msg, key=SECRET_KEY_BYTES):
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

# in reality users passwords would obviously need to be hashed
passwords = {'3dpm': '3dprintersarefun!'}
unrestricted_page_routes = {'/login', '/reauth'}


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if not request.url.path.startswith('/_nicegui') and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@ui.page('/login')
def login():
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if passwords.get(username.value) == password.value:
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
        else:
            ui.notify('Wrong username or password', color='negative')

    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')
    with ui.card().classes('absolute-center'):
        username = ui.input('Username').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)

        def handle_magic():
            ui.navigate.to(f'/reauth?magic_string={magic_string.value}')

        magic_string = ui.input('Magic string').on('keydown.enter', handle_magic)
        ui.button("Reauthenticate using Magic String", on_click=handle_magic)

@ui.page('/reauth')
def reauth(magic_string: str):

    # decode the magic string
    decoded_magic = base64.b64decode(magic_string).decode()
    dict_magic = json.loads(decoded_magic)
    id = dict_magic['id']
    reauthenticate = dict_magic['reauthenticate']

    if hmac_sha256(id.encode()) == reauthenticate:
        # set the browser id
        app.storage.browser['id'] = id
        app.storage.user.update({'authenticated': True})
        return RedirectResponse('/')
    
    else:
        return RedirectResponse('/login')

@ui.page('/upload_test')
def main_page():
    ui.label("Upload test").classes('text-2xl')

    # submit a file
    ui.upload(on_upload=lambda e: process_file(e)).classes('max-w-full')

    def process_file(e):
        print(e) # UploadEventArguments(sender=<nicegui.elements.upload.Upload object at 0x00000214AAB4E270>, client=<nicegui.client.Client object at 0x00000214AAB4DD90>, content=<tempfile.SpooledTemporaryFile object at 0x00000214AA921AE0>, name='justcard.pdf', type='application/pdf')
        # name is accessed by e.content.name
        # type is accessed by e.content.type
        content = e.content
        print("Got file", content)
        
        # save the content to a file
        with open("file", "wb") as f:
            f.write(content.read())

def generate_reauthentication_magic_string():
    # generate a link that the user can click to reauthenticate
    dict_magic = {'id': app.storage.browser['id'], 'reauthenticate': hmac_sha256(app.storage.browser['id'].encode())}

    # base64 encode the dict json dump
    return base64.b64encode(json.dumps(dict_magic).encode()).decode()

@ui.page('/')
def main_page():
    ui.label("Hello, world!").classes('text-2xl')
    # user id at app.storage.browser['id']
    ui.label(f"User ID: {app.storage.browser['id']}")
    
    ui.label("Token-based authentication").classes('text-xl')

    reauth = generate_reauthentication_magic_string()

    async def copy_to_clipboard():
        await ui.run_javascript(f'navigator.clipboard.writeText("{reauth}")')
        ui.notify('Copied to clipboard', color='positive')

    ui.label("If you want to retain your session, copy this link (never expires, so keep it secret):")
    ui.button("Click and copy URL", on_click=copy_to_clipboard)

    ui.label("If you want to ")
    # button to navigate to the upload page
    ui.button('Upload test', on_click=lambda: ui.navigate.to('/upload_test'))

ui.run(storage_secret=SECRET_KEY)