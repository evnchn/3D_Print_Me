import uuid

def generate_uuid():
    return str(uuid.uuid4())

def generate_prefixed_uuid(prefix: str):
    assert "-" not in prefix
    assert len(prefix) > 0
    return f"{prefix}-{generate_uuid()}"

def match_prefixed_uuid(prefix: str, uuid_in: str):
    if not uuid_in.startswith(prefix):
        return ""
    # then get the uuid part
    uuid_part = uuid_in.split("-", 1)[1]
    try:
        return str(uuid.UUID(uuid_part))
    except ValueError:
        return ""
