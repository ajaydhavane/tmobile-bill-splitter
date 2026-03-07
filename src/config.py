import json
import re
from pathlib import Path

USERS_FILE = Path("data/users.json")


def load_config():
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"family_manager": {}, "users": {}}, indent=2))
    return json.loads(USERS_FILE.read_text())


def save_config(config: dict) -> None:
    USERS_FILE.write_text(json.dumps(config, indent=2))


def format_phone(phone: str) -> str:
    nums = re.sub(r"\D", "", phone)
    if len(nums) == 10:
        return f"({nums[:3]}) {nums[3:6]}-{nums[6:]}"
    return phone


def valid_phone(phone: str):
    return len(re.sub(r"\D", "", phone)) == 10


def valid_email(email: str):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
