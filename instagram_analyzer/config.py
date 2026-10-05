import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = DATA_DIR
MAX_CONTENT_LENGTH = None  # 무제한 (Instagram 내보내기 파일 크기 제한 없음)

ALLOWED_EXTENSIONS = {"json", "zip"}

DB_PATH = os.path.join(BASE_DIR, "users.db")

_SECRET_KEY_FILE = os.path.join(BASE_DIR, ".secret_key")


def _load_env_file(path: str) -> None:
    """instagram_analyzer/.env의 KEY=VALUE 줄을 환경변수로 읽어 들인다 (이미 설정된 값은
    덮어쓰지 않는다). 메일 발송 설정처럼 커밋하면 안 되는 값을 두는 곳 — .gitignore 대상."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(os.path.join(BASE_DIR, ".env"))


def get_secret_key() -> bytes:
    """앱 재시작 후에도 세션이 유지되도록 키를 파일에 영구 저장."""
    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, "rb") as f:
            return f.read()
    key = os.urandom(32)
    with open(_SECRET_KEY_FILE, "wb") as f:
        f.write(key)
    return key
