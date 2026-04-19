import uuid


def as_uuid(value: str):
    return uuid.UUID(str(value))
