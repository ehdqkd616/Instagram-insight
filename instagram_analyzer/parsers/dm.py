import json
import logging
import os
import zipfile

from parsers.utils import _fix_str, _ts_to_str

logger = logging.getLogger("instagram_analyzer.parsers.dm")


def detect_dm_my_name(zip_path: str) -> str:
    """ZIP 내 DM 참가자 중 가장 많이 등장하는 이름 = 내 표시 이름."""
    if not os.path.exists(zip_path):
        return ""
    name_freq: dict = {}
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            msg_files = [f for f in zf.namelist()
                         if "/messages/inbox/" in f and f.endswith(".json")]
            for fpath in msg_files:
                try:
                    with zf.open(fpath) as f:
                        data = json.loads(f.read())
                    for p in data.get("participants", []):
                        name = _fix_str(p.get("name", ""))
                        if name:
                            name_freq[name] = name_freq.get(name, 0) + 1
                except Exception:
                    continue
    except Exception:
        return ""
    if not name_freq:
        return ""
    return max(name_freq, key=lambda n: name_freq[n])


def parse_dm_from_zip(zip_path: str, my_name: str) -> list:
    """ZIP에서 내가 참여한 DM 활동(공유·반응·메시지·좋아요)을 파싱."""
    if not os.path.exists(zip_path) or not my_name:
        return []

    activities = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            msg_files = [f for f in zf.namelist()
                         if "/messages/inbox/" in f and f.endswith(".json")]
            logger.info("[dm] DM 파일 수: %d", len(msg_files))

            for fpath in msg_files:
                try:
                    with zf.open(fpath) as f:
                        data = json.loads(f.read())
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue

                thread_title = _fix_str(data.get("title", ""))
                participants = [_fix_str(p.get("name", "")) for p in data.get("participants", [])]
                others = [p for p in participants if p != my_name]
                other_party = others[0] if others else thread_title

                for msg in data.get("messages", []):
                    sender  = _fix_str(msg.get("sender_name", ""))
                    ts_ms   = msg.get("timestamp_ms", 0)
                    ts      = ts_ms // 1000
                    content = _fix_str(msg.get("content", ""))
                    occurred = _ts_to_str(ts)

                    if sender == my_name:
                        if "share" in msg:
                            share = msg["share"]
                            link       = _fix_str(share.get("link", ""))
                            share_text = _fix_str(share.get("share_text", ""))
                            activities.append({
                                "thread_title":  thread_title,
                                "other_party":   other_party,
                                "activity_type": "dm_share",
                                "content":       share_text or link,
                                "link":          link,
                                "timestamp":     ts,
                                "occurred_at":   occurred,
                            })
                        elif content == "Liked a message":
                            activities.append({
                                "thread_title":  thread_title,
                                "other_party":   other_party,
                                "activity_type": "dm_liked",
                                "content":       "메시지에 좋아요",
                                "link":          "",
                                "timestamp":     ts,
                                "occurred_at":   occurred,
                            })
                        elif content:
                            activities.append({
                                "thread_title":  thread_title,
                                "other_party":   other_party,
                                "activity_type": "dm_message",
                                "content":       content[:300],
                                "link":          "",
                                "timestamp":     ts,
                                "occurred_at":   occurred,
                            })

                    for reaction in msg.get("reactions", []):
                        actor = _fix_str(reaction.get("actor", ""))
                        if actor == my_name:
                            emoji = _fix_str(reaction.get("reaction", ""))
                            activities.append({
                                "thread_title":  thread_title,
                                "other_party":   other_party,
                                "activity_type": "dm_reaction",
                                "content":       emoji,
                                "link":          "",
                                "timestamp":     ts,
                                "occurred_at":   occurred,
                            })
    except Exception as e:
        logger.error("[dm] 파싱 오류: %s", e, exc_info=True)

    logger.info("[dm] DM 활동 %d건 파싱 완료 (my_name=%r)", len(activities), my_name)
    return activities
