import logging
import os
import sqlite3

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from config import DATA_DIR, DB_PATH

logger = logging.getLogger("instagram_analyzer.models")


# ── User 모델 ─────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id: int, username: str, password_hash: str,
                 display_name: str = "", instagram_username: str = ""):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.display_name = display_name or username
        self.instagram_username = instagram_username

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def data_dir(self) -> str:
        """계정별 전용 데이터 디렉토리. 없으면 자동 생성."""
        path = os.path.join(DATA_DIR, str(self.id))
        os.makedirs(path, exist_ok=True)
        return path

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"


# ── DB 연결 ───────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """앱 시작 시 테이블 초기화."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                username           TEXT    UNIQUE NOT NULL,
                password_hash      TEXT    NOT NULL,
                display_name       TEXT    DEFAULT '',
                instagram_username TEXT    DEFAULT '',
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    logger.info("DB 초기화 완료: %s", DB_PATH)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, display_name: str = "") -> "User | None":
    """회원 생성. 중복 username이면 None 반환."""
    ph = generate_password_hash(password)
    try:
        with _get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username.strip(), ph, display_name.strip()),
            )
            user_id = cur.lastrowid
        logger.info("신규 사용자 생성: id=%d username=%r", user_id, username)
        return find_user_by_id(user_id)
    except sqlite3.IntegrityError:
        logger.warning("사용자 생성 실패 — 중복 username: %r", username)
        return None


def find_user_by_username(username: str) -> "User | None":
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username "
            "FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row:
        return User(*row)
    return None


def find_user_by_id(user_id: int) -> "User | None":
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username "
            "FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
    if row:
        return User(*row)
    return None


def update_instagram_username(user_id: int, ig_username: str):
    """업로드된 JSON에서 감지한 인스타그램 계정명 저장."""
    with _get_db() as conn:
        conn.execute(
            "UPDATE users SET instagram_username = ? WHERE id = ?",
            (ig_username, int(user_id)),
        )
    logger.info("instagram_username 업데이트: user_id=%d → %r", user_id, ig_username)


def list_users() -> list[User]:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username FROM users"
        ).fetchall()
    return [User(*r) for r in rows]
