import json
import os
import time
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