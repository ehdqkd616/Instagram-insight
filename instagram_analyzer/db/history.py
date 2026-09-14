import json
import logging

from db.connection import _get_db

logger = logging.getLogger("instagram_analyzer.db.history")


def record_upload_snapshot(user_id: int, stats: dict, files_uploaded: list, new_unfollowers: int = 0) -> int:
    with _get_db() as conn:
        cur = conn.execute(
            """INSERT INTO upload_history
               (user_id, files_uploaded, followers_count, following_count,
                mutual_count, not_following_back, only_following_me, new_unfollowers)
               VALUES (?,?,?,?,?,?,?,?)""",
            (int(user_id), json.dumps(files_uploaded, ensure_ascii=False),
             stats.get("followers_count", 0), stats.get("following_count", 0),
             stats.get("mutual_count", 0), stats.get("not_following_back", 0),
             stats.get("only_following_me", 0), new_unfollowers)
        )
        row_id = cur.lastrowid
    logger.info("업로드 히스토리 기록: user_id=%d, id=%d", user_id, row_id)
    return row_id


def get_last_upload_at(user_id: int) -> str:
    """이 사용자의 가장 최근 업로드 시각(직전 스냅샷이 찍힌 시점)을 반환.
    언팔 감지 시 '마지막으로 팔로우가 확인된 시점'의 하한선으로 사용한다."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT uploaded_at FROM upload_history WHERE user_id=? ORDER BY uploaded_at DESC LIMIT 1",
            (int(user_id),)
        ).fetchone()
    return row["uploaded_at"] if row else ""


def get_upload_history(user_id: int) -> list:
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM upload_history WHERE user_id=? ORDER BY uploaded_at DESC",
            (int(user_id),)
        ).fetchall()
    history = []
    for row in rows:
        d = dict(row)
        try:
            d["files_uploaded"] = json.loads(d["files_uploaded"]) if d["files_uploaded"] else []
        except Exception:
            d["files_uploaded"] = []
        history.append(d)
    return history


def delete_upload_history_entry(user_id: int, entry_id: int):
    with _get_db() as conn:
        conn.execute(
            "DELETE FROM upload_history WHERE user_id=? AND id=?",
            (int(user_id), int(entry_id))
        )
    logger.info("업로드 히스토리 삭제: user_id=%d, id=%d", user_id, entry_id)


def get_system_stats() -> dict:
    with _get_db() as conn:
        total_users       = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        admin_users       = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0]
        pending_users     = conn.execute("SELECT COUNT(*) FROM users WHERE status='pending'").fetchone()[0]
        total_uploads     = conn.execute("SELECT COUNT(*) FROM upload_history").fetchone()[0]
        total_dm          = conn.execute("SELECT COUNT(*) FROM dm_activity").fetchone()[0]
        total_unfollowers = conn.execute("SELECT COUNT(*) FROM unfollower_events").fetchone()[0]
        total_snapshots   = conn.execute("SELECT COUNT(*) FROM follower_snapshots").fetchone()[0]
    return {
        "total_users":       total_users,
        "admin_users":       admin_users,
        "pending_users":     pending_users,
        "total_uploads":     total_uploads,
        "total_dm":          total_dm,
        "total_unfollowers": total_unfollowers,
        "total_snapshots":   total_snapshots,
    }
