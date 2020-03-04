import time
import uuid
import secrets


def create_unique_number():
    "Create an unique number"
    epoch = time.time()
    unique_number = "%d" % (epoch)
    return unique_number


def create_uuid():
    "Create an Universally Unique Identifier"
    unique_id = uuid.uuid4()
    return unique_id


def generate_safe_password(password_length):
    "Generate safe passwords"
    safe_password = secrets.token_urlsafe(password_length)
    return safe_password
