import json
import os
import shutil
import time
from nicegui import app
from pydantic import BaseModel
from logic.credentials_management import get_admin_user_from_jwt_token, get_user_from_jwt_token
from logic.jobs_management import fields_check_corelogic, gather_job_corelogic, new_job_corelogic, mark_job_status_corelogic, purge_jobs_corelogic
from fastapi import File, HTTPException, Depends, UploadFile
from fastapi.responses import FileResponse
from typing import Annotated

from logic.jobs_management import raise_user_not_owner_error_corelogic
from logic.jobs_management import UserNotOwnerError

@app.post("/api/job/new_job", responses={
    200: {"description": "Job created successfully", "content": {"application/json": {"example": {"detail": "Job created successfully"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Invalid factory UUID"}}}},
    404: {"description": "Not Found", "content": {"application/json": {"example": {"detail": "Factory description not found"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def new_job(factory: str, current_user: Annotated[str, Depends(get_user_from_jwt_token)]):
    try:
        job_uuid = new_job_corelogic(factory, current_user)
        return {"detail": "Job created successfully", "job_uuid": job_uuid}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SubmitJobFieldsResponseModel(BaseModel):
    job_uuid: str
    fields: dict

@app.post("/api/job/submit_job_fields", responses={
    200: {"description": "Fields submitted successfully", "content": {"application/json": {"example": {"detail": "Fields submitted successfully"}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "[some text to be displayed to the user]"}}}},
    401: {"description": "Unauthorized", "content": {"application/json": {"example": {"detail": "You are not the owner of this job"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def submit_job_fields(response: SubmitJobFieldsResponseModel, current_user: Annotated[str, Depends(get_user_from_jwt_token)]):
    try:
        raise_user_not_owner_error_corelogic(response.job_uuid, current_user)

        all_fields_ready, issues = fields_check_corelogic(response.job_uuid, response.fields)

        if all_fields_ready:
            # write the fields to the job_info.json file, and set the status to 'fields_ready'
            with open(f"jobs/{response.job_uuid}/job_info.json", "r") as f:
                job_info = json.load(f)
                job_info['fields'] = response.fields
                job_info['status'] = 'fields_ready'

        else:
            raise ValueError(";".join(issues))
        
        return {"detail": "Fields submitted successfully"}
    except UserNotOwnerError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/job/process_file", responses={
    200: {"description": "File processed successfully", "content": {"application/json": {"example": {"detail": "File processed successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
# FASTAPI file upload
def process_file(job_uuid: str, current_user: Annotated[str, Depends(get_user_from_jwt_token)], file: UploadFile = File(...)):
    try:
        raise_user_not_owner_error_corelogic(job_uuid, current_user)
        # save the content to a file
        with open(os.path.join("jobs", job_uuid, file.filename), "wb") as f:
            f.write(file.file.read())

        with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
            job_info = json.load(f)
            job_info['status'] = 'submitted'
            # bump the timestamp
            job_info['__timestamp__'] = int(time.time())
            job_info['file'] = file.filename
            with open(f"jobs/{job_uuid}/job_info.json", "w") as f:
                json.dump(job_info, f)
        return {"detail": "File processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/show_jobs", responses={
    200: {"description": "Jobs gathered successfully", "content": {"application/json": {"example": {"detail": "Jobs gathered successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def show_jobs(factory_uuid: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        jobs = gather_job_corelogic(factory_uuid)
        return {"detail": "Jobs gathered successfully", "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/job/purge_jobs", responses={
    200: {"description": "Jobs purged successfully", "content": {"application/json": {"example": {"detail": "Jobs purged successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def purge_jobs(factory_uuid: str, status: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        purge_jobs_corelogic(factory_uuid, status)
        return {"detail": "Jobs purged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/job/mark_as_finished", responses={
    200: {"description": "Job marked as finished successfully", "content": {"application/json": {"example": {"detail": "Job marked as finished successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def mark_as_finished(job_uuid: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        mark_job_status_corelogic(job_uuid, 'finished')
        return {"detail": "Job marked as finished successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/job/mark_as_unfinished", responses={
    200: {"description": "Job marked as unfinished successfully", "content": {"application/json": {"example": {"detail": "Job marked as unfinished successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def mark_as_unfinished(job_uuid: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        mark_job_status_corelogic(job_uuid, 'unfinished')
        return {"detail": "Job marked as unfinished successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/job/download_job", responses={
    200: {"description": "Job downloaded successfully", "content": {"application/json": {"example": {"detail": "Job downloaded successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def download_job(job_uuid: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        with open(f"jobs/{job_uuid}/job_info.json", "r") as f:
            job_info = json.load(f)
            return FileResponse(os.path.join("jobs", job_uuid, job_info['file']))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/job/delete_job", responses={
    200: {"description": "Job deleted successfully", "content": {"application/json": {"example": {"detail": "Job deleted successfully"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["job"])
def delete_job(job_uuid: str, current_user: Annotated[str, Depends(get_admin_user_from_jwt_token)]):
    try:
        shutil.rmtree(f"jobs/{job_uuid}")
        return {"detail": "Job deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))