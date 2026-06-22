import logging
import os
import shutil
import sqlite3

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from config import DATA_DIR
from db.connection import _get_db

logger = logging.getLogger("instagram_analyzer.db.users")


class User(UserMixin):
    def __init__(self, id: int, username: str, password_hash: str,
                 display_name: str = "", instagram_username: str = "", is_admin: int = 0):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.display_name = display_name or username
        self.instagram_username = instagram_username
        self.is_admin = bool(is_admin)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def data_dir(self) -> str:
        path = os.path.join(DATA_DIR, str(self.id))
        os.makedirs(path, exist_ok=True)
        return path

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, display_name: str = "") -> "User | None":
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
            "SELECT id, username, password_hash, display_name, instagram_username, is_admin "
            "FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    return User(*row) if row else None


def find_user_by_id(user_id: int) -> "User | None":
    with _get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username, is_admin "
            "FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
    return User(*row) if row else None


def list_users() -> list:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, password_hash, display_name, instagram_username, is_admin FROM users"
        ).fetchall()
    return [User(*r) for r in rows]


def update_instagram_username(user_id: int, ig_username: str):
    with _get_db() as conn:
        conn.execute(
            "UPDATE users SET instagram_username = ? WHERE id = ?",
            (ig_username, int(user_id)),
        )
    logger.info("instagram_username 업데이트: user_id=%d → %r", user_id, ig_username)


# ── 보안 질문 ─────────────────────────────────────────────────────────────────

def set_security_qa(user_id: int, question: str, answer: str):
    answer_hash = generate_password_hash(answer.strip().lower())
    with _get_db() as conn:
        conn.execute(
            "UPDATE users SET security_question=?, security_answer_hash=? WHERE id=?",
            (question.strip(), answer_hash, int(user_id)),
        )
    logger.info("보안 질문 설정: user_id=%d", user_id)


def get_security_question(user_id: int) -> str:
    with _get_db() as conn:
        row = conn.execute(
            "SELECT security_question FROM users WHERE id=?", (int(user_id),)
        ).fetchone()
    return row[0] if row else ""


def verify_security_answer(user_id: int, answer: str) -> bool:
    with _get_db() as conn:
        row = conn.execute(
            "SELECT security_answer_hash FROM users WHERE id=?", (int(user_id),)
        ).fetchone()
    if not row or not row[0]:
        return False
    return check_password_hash(row[0], answer.strip().lower())


# ── 관리자 전용 ───────────────────────────────────────────────────────────────

def admin_get_all_users() -> list:
    with _get_db() as conn:
        rows = conn.execute("""
            SELECT
                u.id, u.username, u.display_name, u.instagram_username,
                u.is_admin, u.created_at,
                (SELECT COUNT(*) FROM upload_history    WHERE user_id = u.id) AS upload_count,
                (SELECT COUNT(*) FROM dm_activity       WHERE user_id = u.id) AS dm_count,
                (SELECT COUNT(*) FROM follower_snapshots WHERE user_id = u.id) AS snapshot_count,
                (SELECT COUNT(*) FROM unfollower_events  WHERE user_id = u.id) AS unfollower_count
            FROM users u ORDER BY u.id
        """).fetchall()
    return [dict(r) for r in rows]


def admin_update_user(user_id: int, display_name: str = None,
                      is_admin: bool = None, new_password: str = None):
    fields, params = [], []
    if display_name is not None:
        fields.append("display_name=?")
        params.append(display_name)
    if is_admin is not None:
        fields.append("is_admin=?")
        params.append(1 if is_admin else 0)
    if new_password:
        fields.append("password_hash=?")
        params.append(generate_password_hash(new_password))
    if not fields:
        return
    params.append(int(user_id))
    with _get_db() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", params)
    logger.info("관리자가 사용자 수정: user_id=%d fields=%s", user_id, fields)


def admin_delete_user(user_id: int):
    uid = int(user_id)
    with _get_db() as conn:
        for table in ("dm_activity", "follower_snapshots", "unfollower_events",
                      "upload_history", "user_settings"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
    data_dir = os.path.join(DATA_DIR, str(uid))
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    logger.info("사용자 삭제 완료: user_id=%d", uid)
