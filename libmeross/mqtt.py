from libmeross import util


def generate_device_client_id(uuid: str, shared_nonce: str | None = None) -> str:
    return f"fmware:{uuid}_{shared_nonce or util.generate_random(16)}"


def generate_password(user_id: int, mac: str, shared_key: str | None = None) -> str:
    pwd_hash = util.hash_password(f"{mac}{shared_key or ''}")
    return f"{user_id}_{pwd_hash}"
