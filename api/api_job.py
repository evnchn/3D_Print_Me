from nicegui import app
from logic.credentials_management import get_user_from_jwt_token
from logic.jobs_management import new_job_corelogic
from fastapi import HTTPException, Depends
from typing import Annotated

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