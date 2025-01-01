from glob import glob
import json
import os
import shutil
import time

from nicegui import ui
from utils.uuid_handling import generate_prefixed_uuid, match_prefixed_uuid

def new_job_corelogic(factory: str, username: str) -> str:
    # assert that the factory exists
    if not match_prefixed_uuid("factory", factory):
        raise ValueError("Invalid factory UUID")
    if not os.path.exists(f"factories/{factory}/desc.json"):
        raise FileNotFoundError("Factory description not found")

    # creates /jobs/{random UUID} folder
    # writes the job_info.json file
    my_uuid = generate_prefixed_uuid("job")
    os.makedirs(f"jobs/{my_uuid}")
    with open(f"jobs/{my_uuid}/job_info.json", "w") as f:
        json.dump({'factory': factory, 'status': 'new', '__timestamp__': int(time.time()), '__user__': username}, f)

    return my_uuid

def fields_check_corelogic(job_uuid: str, fields: dict):
    # do some validation on some of the fields which the framework does NOT promise to do

    # first of all, check if the field is present in the job_info
    # then, it must be non-empty
    # email is handle by the browser, and it is not obliged to provide a valid email
    # so we need to validate it here

    issues = []

    with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
        job_info = json.load(f)
        for field in fields:
            if field['name'] not in job_info.get("fields", {}):
                if field.get('__default__', ""):
                    issues.append(f"Field {field['name']} is missing. Click submit to use the default value")
                else:
                    issues.append(f"Field {field['name']} is missing")
            elif not job_info.get("fields", {}).get(field['name'], ""):
                issues.append(f"Field {field['name']} is empty")
            elif field.get('__format__', '') == 'email' and not "@" in job_info.get("fields", {}).get(field['name'], ""):
                if job_info.get("fields", {}).get(field['name'], ""):
                    issues.append(f"Field {field['name']} is not a valid email")
    all_fields_ready = not bool(issues)
    return all_fields_ready, issues


def gather_job_corelogic(factory_uuid: str):
    jobs = []
    for job in glob(f"jobs/*"):
        with open(f"{job}/job_info.json", "r") as f:
            job_info = json.load(f)
            if factory_uuid == "__all__" or job_info.get('factory_uuid') == factory_uuid:
                jobs.append(job_info)
    return jobs

def purge_jobs_corelogic(factory_uuid: str, status: str):
    jobs = gather_job_corelogic(factory_uuid)
    for job in jobs:
        if job['status'] == status:
            shutil.rmtree(f"jobs/{job['uuid']}")
    ui.navigate.to(f"/show_jobs/{factory_uuid}")


def mark_job_status_corelogic(job_uuid_2, status):
    with open(f"jobs/{job_uuid_2}/job_info.json", "r") as f:
        job_info = json.load(f)
        job_info['status'] = status
        with open(f"jobs/{job_uuid_2}/job_info.json", "w") as f:
            json.dump(job_info, f)
    ui.navigate.reload()


class UserNotOwnerError(Exception):
    pass


def raise_user_not_owner_error_corelogic(job_uuid: str, current_user: str):
    with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
        job_info = json.load(f)
        if job_info.get('__user__', '') != current_user:
            raise UserNotOwnerError("You are not the owner of this job")
        