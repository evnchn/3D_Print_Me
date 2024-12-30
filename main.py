# Core libraries
import hashlib
import hmac
import json
import base64
import shutil
from glob import glob
import os

# NiceGUI libraries
from nicegui import ui, app
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Our custom libraries
from utils.auth import hash_new_password, is_correct_password, serialize_bytes_to_str, deserialize_str_to_bytes
from utils.uuid_handling import generate_prefixed_uuid, match_prefixed_uuid
from utils.patch_css import patch_markdown_font_size

# Load the environment variables
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY_BYTES = SECRET_KEY.encode()
DEBUGMODE = int(os.getenv("DEBUGMODE", 0))

# Boot indication
print("All imports successful")
print("Debug mode:", DEBUGMODE)

# Always use indentation in the storage files
app.storage.general.indent = True
app.storage.general.backup()
for user_storage in app.storage._users.values():
    user_storage.indent = True
    user_storage.backup()

# assert that the factories folder exists, and that all subfolders are named with factory uuid
if not os.path.exists("factories"):
    os.makedirs("factories")
for factory in glob("factories/*"):
    if not match_prefixed_uuid("factory", os.path.basename(factory)):
        # rename the folder
        print("Renaming", factory)
        new_path = os.path.join(os.path.dirname(factory), generate_prefixed_uuid("factory"))
        os.rename(factory, new_path)

# in reality users passwords would obviously need to be hashed
passwords = {'3dpm': '3dprintersarefun!', 'admin': 'topsecret'}
priviledged_users = {'admin'}
unrestricted_page_routes = {'/login', '/reauth'}


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if not request.url.path.startswith('/_nicegui') and request.url.path not in unrestricted_page_routes:
                return RedirectResponse('/login')
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@ui.page('/login')
def login():
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if passwords.get(master_username.value) == master_password.value:
            # add the username and password to app.storage.general['user_pw'], if not exist create dict
            if 'user_pw' not in app.storage.general:
                app.storage.general['user_pw'] = {}

            # check if the username already exists
            if username.value in app.storage.general['user_pw']:
                ui.notify('Username already exists', color='negative')
                return
            
            # if the account was created with a master username-password set that is in the priviledged_users set, admin=True
            is_admin = master_username.value in priviledged_users
            # hash the password and store the salt and hash
            salt, pw_hash = hash_new_password(password.value)
            app.storage.general['user_pw'][username.value] = {'salt': serialize_bytes_to_str(salt), 'pw_hash': serialize_bytes_to_str(pw_hash), 'admin': is_admin}
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to("/")
        else:
            ui.notify('Wrong username or password', color='negative')

    def try_login_2() -> None:  # local function to avoid passing username and password as arguments
        # first check if the username exists
        if not app.storage.general.get('user_pw', {}).get(username_2.value):
            ui.notify('Wrong username or password', color='negative')
        else:
            # get the salt and hash from the storage
            salt = deserialize_str_to_bytes(app.storage.general['user_pw'][username_2.value]['salt'])
            pw_hash = deserialize_str_to_bytes(app.storage.general['user_pw'][username_2.value]['pw_hash'])
            # check if the password is correct
            if is_correct_password(salt, pw_hash, password_2.value):
                app.storage.user.update({'username': username_2.value, 'authenticated': True})
                ui.navigate.to("/")
            else:
                ui.notify('Wrong username or password', color='negative')

    with ui.card().classes('absolute-center'):
        ui.label("Create a new account").classes('text-2xl')
        master_username = ui.input('Master Username').classes("w-full")
        master_username.on('keydown.enter', try_login)
        master_password = ui.input('Master Password', password=True, password_toggle_button=True).classes("w-full")
        master_password.on('keydown.enter', try_login)
        if DEBUGMODE:
            # populate the master username and password
            a_set_of_values = list(passwords.items())[0]
            master_username.value = a_set_of_values[0]
            master_password.value = a_set_of_values[1]
        username = ui.input('Username').classes("w-full")
        username.on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).classes("w-full")
        password.on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)

        ui.label("Login").classes('text-2xl')
        username_2 = ui.input('Username').classes("w-full")
        username_2.on('keydown.enter', try_login_2)
        password_2 = ui.input('Password', password=True, password_toggle_button=True).classes("w-full")
        password_2.on('keydown.enter', try_login_2)
        ui.button('Log in', on_click=try_login_2)

@ui.page('/')
def main_page():
    ui.label("Hello, world!").classes('text-2xl')
    username = app.storage.user.get('username', 'not logged in?')
    ui.label(f"Logged in as {username}")
    is_admin = app.storage.general.get('user_pw', {}).get(username, {}).get('admin', False)
    admin_text = "Admin" if is_admin else "Not Admin"
    ui.label(admin_text)

    # button to navigate to the factories page
    ui.button('Factories', on_click=lambda: ui.navigate.to('/show_factories'))

@ui.page("/show_factories")
def show_factories():
    patch_markdown_font_size()
    ui.label("Factories").classes('text-2xl')

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
                    ui.image(f"{factory}/{desc['cover_image']}").classes("w-full h-96").props("fit='contain' ratio=1")
                    ui.button("New Job", on_click=lambda factory=basename: new_job_to_factory(factory))
                    ui.button("Show Jobs", on_click=lambda factory=basename: show_jobs_at_factory(factory))

@ui.page("/new_job_to_factory/{factory}")
def new_job_to_factory(factory: str):
    # assert that the factory exists
    if not match_prefixed_uuid("factory", factory):
        return ui.navigate.to("/show_factories")
    if not os.path.exists(f"factories/{factory}/desc.json"):
        return ui.navigate.to("/show_factories")

    # creates /jobs/{random UUID} folder
    # writes the job_info.json file
    # my_uuid = generate_uuid()
    my_uuid = generate_prefixed_uuid("job")
    os.makedirs(f"jobs/{my_uuid}")
    with open(f"jobs/{my_uuid}/job_info.json", "w") as f:
        json.dump({'factory': factory, 'status': 'new'}, f)

    ui.navigate.to(f"/submit_to_factory/{my_uuid}")

@ui.page("/submit_to_factory/{job_uuid}")
def submit_to_factory(job_uuid: str):
    patch_markdown_font_size()
    # assert that the job_uuid exists
    if not match_prefixed_uuid("job", job_uuid):
        return ui.navigate.to("/")
    if not os.path.exists(f"jobs/{job_uuid}/job_info.json"):
        return ui.navigate.to("/")

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
                        ui.label(f"Status: {job_info['status']}")
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
        ui.label(f"Status: {job_info['status']}")

    if job_info['status'] == 'submitted':
        ui.button("Download Job", on_click=lambda job_uuid=job_uuid: download_job(job_uuid))

    ui.button("Delete Job", on_click=lambda job_uuid=job_uuid: delete_job(job_uuid))



ui.run(storage_secret=SECRET_KEY)
