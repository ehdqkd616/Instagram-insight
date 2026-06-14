import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = DATA_DIR
MAX_CONTENT_LENGTH = None  # 무제한 (Instagram 내보내기 파일 크기 제한 없음)

ALLOWED_EXTENSIONS = {"json", "zip"}

DB_PATH = os.path.join(BASE_DIR, "users.db")

_SECRET_KEY_FILE = os.path.join(BASE_DIR, ".secret_key")


def get_secret_key() -> bytes:
    """앱 재시작 후에도 세션이 유지되도록 키를 파일에 영구 저장."""
    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, "rb") as f:
            return f.read()
    key = os.urandom(32)
    with open(_SECRET_KEY_FILE, "wb") as f:
        f.write(key)
    return key
