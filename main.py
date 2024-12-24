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

import uuid
import shutil

def generate_uuid():
    return str(uuid.uuid4())

from glob import glob

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
        # name is accessed by e.name
        # type is accessed by e.type
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

    """ui.label("If you want to ")
    # button to navigate to the upload page
    ui.button('Upload test', on_click=lambda: ui.navigate.to('/upload_test'))"""

    # button to navigate to the factories page
    ui.button('Factories', on_click=lambda: ui.navigate.to('/show_factories'))


@ui.page("/show_factories")
def show_factories():
    ui.label("Factories").classes('text-2xl')
    ui.label("This page is restricted to authenticated users")

    # list all the factories
    ui.label("List of factories")

    def new_job_to_factory(factory):
        ui.navigate.to(f"/new_job_to_factory/{factory}")

    def show_jobs_at_factory(factory):
        ui.navigate.to(f"/show_jobs/{factory}")
    
    with ui.column().classes("w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"):
        # enumerate factories folder, for each subfolder, try open desc.json
        for factory in glob("factories/*"):
            basename = os.path.basename(factory)
            with open(f"{factory}/desc.json", "r") as f:
                desc = json.load(f)
                with ui.card().classes("w-full"):
                    ui.label(f"Factory: {desc['name']}").classes('text-xl')
                    ui.markdown(desc['description'])
                    ui.markdown(desc['upload_instructions'])
                    ui.image(f"{factory}/{desc['cover_image']}").classes("w-full h-96").props("fit='contain'")
                    ui.button("New Job", on_click=lambda factory=basename: new_job_to_factory(factory))
                    ui.button("Show Jobs", on_click=lambda factory=basename: show_jobs_at_factory(factory))

@ui.page("/new_job_to_factory/{factory}")
def new_job_to_factory(factory: str):
    # creates /jobs/{random UUID} folder
    # writes the job_info.json file
    my_uuid = generate_uuid()
    os.makedirs(f"jobs/{my_uuid}")
    with open(f"jobs/{my_uuid}/job_info.json", "w") as f:
        json.dump({'factory': factory, 'status': 'new'}, f)

    ui.navigate.to(f"/submit_to_factory/{my_uuid}")

@ui.page("/submit_to_factory/{job_uuid}")
def submit_to_factory(job_uuid: str):

    all_fields_ready = True

    input_elems = {}
    # read the job_info.json file
    with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
        job_info = json.load(f)
        if job_info['status'] == 'submitted':
            return ui.navigate.to("/")
        factory = job_info['factory']
        with open(f"factories/{factory}/desc.json", "r") as f:
            desc = json.load(f)
            ui.label(f"Factory: {desc['name']}").classes('text-2xl')
            ui.markdown(desc['upload_instructions'])
            fields = desc.get('fields', []) 
            for field in fields:
                if field['name'] not in job_info.get("fields", {}):
                    all_fields_ready = False
                
                input_elems[field['name']] = ui.input(field['name'], placeholder=field['description'], value=job_info.get("fields", {}).get(field['name'], ""))
            
            def submit_job_fields():
                job_info['fields'] = {}
                for field in fields:
                    job_info["fields"][field['name']] = input_elems[field['name']].value
                job_info['status'] = 'fields_ready'
                with open(f"jobs/{job_uuid}/job_info.json", "w") as f:
                    json.dump(job_info, f)
                ui.navigate.to(f"/submit_to_factory/{job_uuid}")

            ui.button("Submit", on_click=submit_job_fields)
            upload_elem = ui.upload(on_upload=lambda e: process_file(e, job_uuid)).classes('max-w-full').props(f"accept='{desc.get('accepted_file_types', '*')}'")
            upload_elem.set_enabled(all_fields_ready)

    def process_file(e, job_uuid):
        print(e)
        content = e.content
        print("Got file", content)

        # save the content to a file
        with open(f"jobs/{job_uuid}/{e.name}", "wb") as f:
            f.write(content.read())

        with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
            job_info = json.load(f)
            job_info['status'] = 'submitted'
            job_info['file'] = e.name
            with open(f"jobs/{job_uuid}/job_info.json", "w") as f:
                json.dump(job_info, f)

        ui.navigate.to("/")

@ui.page("/show_jobs/{factory}")
def show_jobs(factory: str):
    ui.label(f"Jobs at {factory}").classes('text-2xl')
    with ui.column().classes("w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"):
        for job in glob(f"jobs/*"):
            basename = os.path.basename(job)
            with open(f"{job}/job_info.json", "r") as f:
                job_info = json.load(f)
                if job_info['factory'] == factory:
                    with ui.card().classes("w-full"):
                        ui.label(f"Job ID: {job}").classes('text-xl')
                        ui.markdown(f"Status: {job_info['status']}")
                        ui.button("View Job", on_click=lambda basename=basename: ui.navigate.to(f"/show_job/{basename}"))

@ui.page("/show_job/{job_uuid}")
def show_job(job_uuid: str):
    if not job_uuid:
        return ui.navigate.to("/")

    print("viewing job", job_uuid)
    def download_job(job_uuid_2):
        print("downloading job", job_uuid_2)
        # use ui.download to download the job
        with open(f"jobs/{job_uuid_2}/job_info.json", "r") as f:
            job_info = json.load(f)
            ui.download(f"jobs/{job_uuid_2}/{job_info['file']}")

    def delete_job(job_uuid_2):
        print("deleting job", job_uuid_2)
        # use ui.download to download the job
        
        shutil.rmtree(f"jobs/{job_uuid_2}")
        ui.navigate.to("/")

    with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
        job_info = json.load(f)
        ui.label(f"Job ID: {job_uuid}").classes('text-2xl')
        for field, value in job_info.get("fields", {}).items():
            ui.label(f"{field}: {value}")
        ui.markdown(f"Status: {job_info['status']}")

    if job_info['status'] == 'submitted':
        ui.button("Download Job", on_click=lambda job_uuid=job_uuid: download_job(job_uuid))

    ui.button("Delete Job", on_click=lambda job_uuid=job_uuid: delete_job(job_uuid))



ui.run(storage_secret=SECRET_KEY)
