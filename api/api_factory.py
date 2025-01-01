from glob import glob
import json
import os
from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app

"""@ui.page("/show_factories")
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
                        ui.button("Show Jobs", on_click=lambda factory=basename: show_jobs_at_factory(factory))"""

@app.get("/api/factory/get_all_factories", responses={
    200: {"description": "All factories retrieved successfully", "content": {"application/json": {"example": {"detail": "All factories retrieved successfully", "factories": ["factory-deadbeef-dead-dead-dead-deaddeafbeef-dead-dead-dead-deaddeafbeef"]}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["factory"])
def get_all_factories():
    try:
        factories = {}
        for factory in glob("factories/*"):
            passthrough_keys = ["name", "description", "upload_instructions", "cover_image"]
            # open desc.json and get the keys to pass through
            with open(f"{factory}/desc.json", "r") as f:
                desc = json.load(f)
                factories[os.path.basename(factory)] = {k: desc.get(k) for k in passthrough_keys}
        return {"detail": "All factories retrieved successfully", "factories": factories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/factory/get_factory", responses={
    200: {"description": "Factory retrieved successfully", "content": {"application/json": {"example": {"detail": "Factory retrieved successfully", "factory": {"name": "factory-deadbeef-dead-dead-dead-deaddeafbeef", "description": "This is a factory", "owner": "user-deadbeef-dead-dead-dead-deaddeafbeef"}}}}},
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "Factory not found"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["factory"])
def get_factory(factory_id: str):
    try:
        factory = glob(f"factories/{factory_id}")
        if not factory:
            raise HTTPException(status_code=400, detail="Factory not found")
        with open(f"{factory[0]}/desc.json", "r") as f:
            desc = json.load(f)
        return {"detail": "Factory retrieved successfully", "factory": desc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# get factory attachments (images, etc)
@app.get("/api/factory/get_factory_attachments", responses={
    400: {"description": "Bad Request", "content": {"application/json": {"example": {"detail": "File not found"}}}},
    500: {"description": "Internal Server Error", "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}}
}, tags=["factory"])
def get_factory_attachments(factory_id: str, filename: str):
    try:
        factory = glob(f"factories/{factory_id}")
        if not factory:
            raise HTTPException(status_code=400, detail="Factory not found")
        # serve the file at factories/{factory_id}/{filename}, be sure to avoid directory traversal

        filename = os.path.basename(filename) # avoid directory traversal
        path_of_file = os.path.join(factory[0], filename)

        if not os.path.exists(path_of_file):
            raise HTTPException(status_code=400, detail="File not found")
        
        return FileResponse(path_of_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))