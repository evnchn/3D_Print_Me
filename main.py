# Core libraries
import json
import shutil
from glob import glob
import os
import time

# NiceGUI libraries
from nicegui import ui, app

# Our custom libraries
from logic.credentials_management import (
    create_user_corelogic,
    check_credentials_corelogic,
    CheckCredentialsResponseModel,
    CreateUserResponseModel,
    WrongCredentialsError,
    UsernameExistsError,
    NullUserFieldError
)
from logic.jobs_management import new_job_corelogic
from logic.jobs_management import fields_check_corelogic
from logic.jobs_management import gather_job_corelogic
from logic.jobs_management import purge_jobs_corelogic
from logic.jobs_management import mark_job_status_corelogic
from utils.security_definitions import passwords, AuthMiddleware
from unified_header_lib.unified_header import unified_header
from utils.uuid_handling import generate_prefixed_uuid, match_prefixed_uuid
from utils.patch_css import patch_markdown_font_size

# define API access routes
from api import api_userauth
from api import sample_secure_endpoint
from api import api_factory
from api import api_job

# Load the environment variables
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
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
for factory_scan in glob("factories/*"):
    if not match_prefixed_uuid("factory", os.path.basename(factory_scan)):
        # rename the folder
        print("Renaming", factory_scan)
        new_path = os.path.join(os.path.dirname(factory_scan), generate_prefixed_uuid("factory"))
        os.rename(factory_scan, new_path)

# in reality users passwords would obviously need to be hashed
app.add_middleware(AuthMiddleware)

@ui.page('/register')
def register():
    def try_create_user() -> None:
        response = CreateUserResponseModel(
            master_username=master_username.value,
            master_password=master_password.value,
            username=username.value,
            password=password.value
        )
        try:
            if create_user_corelogic(response):
                ui.navigate.to("/")
        except (WrongCredentialsError, UsernameExistsError, NullUserFieldError) as e:
            ui.notify(str(e), color='negative')

    with ui.card().classes('absolute-center'):
        ui.label("Create a new account").classes('text-2xl')
        master_username = ui.input('Master Username').classes("w-full")
        master_username.on('keydown.enter', try_create_user)
        master_password = ui.input('Master Password', password=True, password_toggle_button=True).classes("w-full")
        master_password.on('keydown.enter', try_create_user)
        if DEBUGMODE:
            # populate the master username and password
            a_set_of_values = list(passwords.items())[0]
            master_username.value = a_set_of_values[0]
            master_password.value = a_set_of_values[1]
        username = ui.input('Username').classes("w-full")
        username.on('keydown.enter', try_create_user)
        password = ui.input('Password', password=True, password_toggle_button=True).classes("w-full")
        password.on('keydown.enter', try_create_user)
        ui.button('Register', on_click=try_create_user)
        ui.link('Login', '/login')

@ui.page('/login')
def login():
    def try_login() -> None:
        response = CheckCredentialsResponseModel(
            username=username_2.value,
            password=password_2.value
        )
        try:
            result = check_credentials_corelogic(response)
            app.storage.user.update({'username': response.username, 'authenticated': True})
            ui.navigate.to("/")
        except (WrongCredentialsError, NullUserFieldError) as e:
            ui.notify(str(e), color='negative')

    with ui.card().classes('absolute-center'):
        ui.label("Login").classes('text-2xl')
        username_2 = ui.input('Username').classes("w-full")
        username_2.on('keydown.enter', try_login)
        password_2 = ui.input('Password', password=True, password_toggle_button=True).classes("w-full")
        password_2.on('keydown.enter', try_login)
        ui.button('Log in', on_click=try_login)
        ui.link('Register', '/register')

@ui.page('/')
def main_page():
    def logout() -> None:
        app.storage.user.update({'authenticated': False})
        ui.navigate.to("/login")
    with unified_header("Main Page"):
        ui.button("Logout", on_click=logout).classes("shrink-0")
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
    is_admin = app.storage.general.get('user_pw', {}).get(app.storage.user.get('username', ''), {}).get('admin', False)
    with unified_header("Factories", "/"):
        # if is admin, show a button to show all jobs across all factories
        if is_admin:
            ui.button("Show All Jobs", on_click=lambda: ui.navigate.to("/show_jobs/__all__"))

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
                    # show jobs button for admin only
                    if is_admin:
                        ui.button("Show Jobs", on_click=lambda factory=basename: show_jobs_at_factory(factory))

@ui.page("/new_job_to_factory/{factory}")
def new_job_to_factory(factory: str):
    username = app.storage.user.get('username', '')
    if not username:  # not logged in
        ui.label("You need to be logged in to submit a job")
    try:
        job_uuid = new_job_corelogic(factory, username)
        ui.navigate.to(f"/submit_to_factory/{job_uuid}")
    except (ValueError, FileNotFoundError) as e:
        ui.notify(str(e), color='negative')
        ui.navigate.to("/show_factories")

@ui.page("/submit_to_factory/{job_uuid}")
def submit_to_factory(job_uuid: str):
    patch_markdown_font_size()
    # assert that the job_uuid exists
    if not match_prefixed_uuid("job", job_uuid):
        return ui.navigate.to("/")
    if not os.path.exists(f"jobs/{job_uuid}/job_info.json"):
        return ui.navigate.to("/")

    all_fields_ready = True
    issues = []

    input_elems = {}
    # read the job_info.json file
    with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
        job_info = json.load(f)
        if job_info['status'] == 'submitted':
            return ui.navigate.to("/")
        factory = job_info['factory']
        with open(f"factories/{factory}/desc.json", "r") as f:
            desc = json.load(f)
            with unified_header(f"Factory: {desc['name']}", "/show_factories"):
                pass

            # given the job UUID, show a random cat by https://robohash.org/{UUID}.png?set=set4&size=128x128
            ui.image(f"https://robohash.org/{job_uuid}.png?set=set4&size=128x128").classes("w-32 h-32") # set=set4 is cats

            ui.markdown(desc['upload_instructions'])
            fields = desc.get('fields', []) 
            
            all_fields_ready, issues = fields_check_corelogic(job_uuid, fields)

            for field in fields:

                        
                """The JSON specifies special underscore-prefixed features for field validation:

1. **`__limited_choice__`**: Defines a set of allowed values for a field, as well as **`__limited_choice_text__`** to provide a description for each value.
2. [DEPRECATED] **`__lower_limit__` and `__upper_limit__`**: Establish numerical constraints for input ranges.
3. **`__format__`**: Specifies the expected format for certain inputs. Valid values are only "email" as of now. 
4. **`__default__`**: Provides a default value for a field.

These features ensure valid and appropriate data entry for each field."""

                name = field['name']
                ui.label(name).classes('text-xl')
                description = field['description']
                ui.label(description)
                default_value = field.get('__default__', "")
                # if job_info already has a value for this field, use that
                if name in job_info.get("fields", {}):
                    default_value = job_info["fields"][name]
                if '__limited_choice__' in field:
                    options = field['__limited_choice__']
                    if not default_value in options:
                        default_value = "" # there is an issue, but fail silently
                    if '__limited_choice_text__' in field:
                        options = {options[i]: field['__limited_choice_text__'][i] for i in range(len(options))}
                    print("Debugging options", options)
                    input_elems[name] = ui.select(options=options, value=default_value).classes("w-full")
                elif '__format__' in field and field['__format__'] == 'email':
                    input_elems[name] = ui.input(value=default_value).props("type='email'").classes("w-full")
                else:
                    input_elems[name] = ui.input(value=default_value).classes("w-full")
            
            def submit_job_fields():
                job_info['fields'] = {}
                for field in fields:
                    job_info["fields"][field['name']] = input_elems[field['name']].value
                all_fields_ready, issues = fields_check_corelogic(job_uuid, fields)
                if all_fields_ready:
                    job_info['status'] = 'fields_ready'
                else:
                    job_info['status'] = 'fields_incomplete'
                with open(f"jobs/{job_uuid}/job_info.json", "w") as f:
                    json.dump(job_info, f)
                ui.navigate.reload()

            ui.button("Submit", on_click=submit_job_fields)
            # show the issues
            for issue in issues:
                ui.label(issue).classes('text-red-500')
            upload_elem = ui.upload(on_upload=lambda e: process_file(e, job_uuid)).classes('max-w-full').props(f"accept='{desc.get('accepted_file_types', '*')}'")
            upload_elem.set_enabled(all_fields_ready)

    def process_file(e, job_uuid):
        print(e)
        content = e.content
        print("Got file", content)

        # establish safe name to prevent path traversal
        safe_name = os.path.basename(e.name)

        # save the content to a file
        with open(os.path.join("jobs", job_uuid, safe_name), "wb") as f:
            f.write(content.read())

        with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
            job_info = json.load(f)
            job_info['status'] = 'submitted'
            # bump the timestamp
            job_info['__timestamp__'] = int(time.time())
            job_info['file'] = safe_name
            with open(f"jobs/{job_uuid}/job_info.json", "w") as f:
                json.dump(job_info, f)

        ui.navigate.to("/")

@ui.page("/show_jobs/{factory_uuid}")
def show_jobs(factory_uuid: str):
    # assert that the factory exists, allow "__all__" to show all jobs
    if factory_uuid != "__all__":
        if not match_prefixed_uuid("factory", factory_uuid):
            return ui.navigate.to("/show_factories")
        if not os.path.exists(f"factories/{factory_uuid}/desc.json"):
            return ui.navigate.to("/show_factories")
    
    # this page is limited to admins
    is_admin = app.storage.general.get('user_pw', {}).get(app.storage.user.get('username', ''), {}).get('admin', False)
    if not is_admin:
        return ui.navigate.to("/show_factories")
    
    jobs = gather_job_corelogic(factory_uuid)
    
    def purge_new_jobs():
        purge_jobs_corelogic(factory_uuid, 'new')

    def purge_incomplete_jobs():
        purge_jobs_corelogic(factory_uuid, 'fields_incomplete')

    def purge_finished_jobs():
        purge_jobs_corelogic(factory_uuid, 'finished')

    def purge_unfinished_jobs():
        purge_jobs_corelogic(factory_uuid, 'unfinished')

    def mark_as_finished(job_uuid_2):
        mark_job_status_corelogic(job_uuid_2, 'finished')

    def mark_as_unfinished(job_uuid_2):
        mark_job_status_corelogic(job_uuid_2, 'unfinished')

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
        ui.navigate.reload()

    with ui.dialog() as dialog_batch_delete, ui.card():
        ui.button("Purge New Jobs (the empty jobs)", on_click=purge_new_jobs, color="red").classes("w-full")
        ui.button("Purge Incomplete Jobs (may affect students!)", on_click=purge_incomplete_jobs, color="red").classes("w-full")
        ui.button("Purge Finished Jobs (the old jobs)", on_click=purge_finished_jobs, color="red").classes("w-full")
        ui.button("Purge Rejected Jobs (technician reject, student no response)", on_click=purge_unfinished_jobs, color="red").classes("w-full")
    
    if factory_uuid == "__all__":
        with unified_header("Jobs at All Factories", "/show_factories"):
            ui.button("Batch delete", on_click=dialog_batch_delete.open, color="red").classes("shrink-0")
        # populate dict names_of_all_factories
        names_of_all_factories = {}
        for factory_file in glob("factories/*"):
            with open(f"{factory_file}/desc.json", "r") as f:
                desc = json.load(f)
                names_of_all_factories[os.path.basename(factory_file)] = desc['name']
    else:
        with open(f"factories/{factory_uuid}/desc.json", "r") as f:
            desc = json.load(f)
            with unified_header(f"Jobs at {desc['name']}", "/show_factories"):
                ui.button("Batch delete", on_click=dialog_batch_delete.open, color="red").classes("shrink-0")



    with ui.column().classes("w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"):
        jobs = []
        for job in glob(f"jobs/*"):
            with open(f"{job}/job_info.json", "r") as f:
                job_info = json.load(f)
                if factory_uuid == "__all__" or job_info['factory'] == factory_uuid:
                    jobs.append((job, job_info))

        print("jobs", jobs)

        sorted_jobs = sorted(jobs, key=lambda x: x[1].get('__timestamp__', 0))

        for job, job_info in sorted_jobs:
            basename = os.path.basename(job)
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full"):
                    with ui.column().classes("flex-grow"):
                        ui.label(f"Status: {job_info['status']}").classes('text-xl')
                        ui.label(basename)
                    # show a random cat, basename is the uuid
                    ui.image(f"https://robohash.org/{basename}.png?set=set4&size=128x128").classes("w-16 h-16 shrink-0")

                # if factory == "__all__", show the factory name
                if factory_uuid == "__all__":
                    ui.label(f"Factory: {names_of_all_factories[job_info['factory']]}")
                ui.separator()
                for field, value in job_info.get("fields", {}).items():
                    ui.label(f"{field}: {value}")
                ui.separator()
                # ui.button("View Job", on_click=lambda basename=basename: ui.navigate.to(f"/show_job/{basename}"))
                with ui.row().classes("w-full"):
                    # BUTTON 1: Download
                    ui.button("Download", on_click=lambda basename=basename: download_job(basename)).classes("flex-grow basis-0").set_enabled(job_info['status'] == 'submitted')

                    # BUTTON 2: Delete
                    ui.button("Delete", on_click=lambda basename=basename: delete_job(basename)).classes("flex-grow basis-0")

                with ui.row().classes("w-full"):
                    # BUTTON 3: Mark as Finished
                    ui.button("Finish", on_click=lambda basename=basename: mark_as_finished(basename)).classes("flex-grow basis-0").set_enabled(job_info['status'] != 'finished')
                    
                    # BUTTON 4: Mark as Unfinished
                    ui.button("Reject", on_click=lambda basename=basename: mark_as_unfinished(basename)).classes("flex-grow basis-0").set_enabled(job_info['status'] != 'unfinished')


ui.run(storage_secret=SECRET_KEY, fastapi_docs=True)