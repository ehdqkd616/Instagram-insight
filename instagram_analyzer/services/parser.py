import json
import logging
import os
import zipfile
from datetime import datetime

logger = logging.getLogger("instagram_analyzer.parser")


def _ts_to_str(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _fix_str(s: str) -> str:
    """Instagram이 한글을 Latin-1 mojibake로 내보낸 경우 UTF-8로 복원.
    예: 'ì\\x82¬ì\\x9a©...' → '사용자 이름'  /  이미 올바른 UTF-8이면 그대로 반환.
    """
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _load_json(path, label):
    if not os.path.exists(path):
        logger.debug("[%s] 파일 없음: %s", label, path)
        return None
    size_kb = os.path.getsize(path) / 1024
    logger.debug("[%s] 파싱 시작 (%.1f KB): %s", label, size_kb, os.path.basename(path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.debug("[%s] 파싱 완료", label)
    return data


def parse_followers(data_dir):
    """followers_1.json -> list of {username, profile_url, followed_at, timestamp}

    형식: 최상위 배열
    [{"title": "", "string_list_data": [{"href": "...", "value": "username", "timestamp": 123}]}]
    """
    raw = _load_json(os.path.join(data_dir, "followers_1.json"), "followers")
    if raw is None:
        return []

    results = []
    for item in raw:
        for entry in item.get("string_list_data", []):
            results.append({
                "username":    entry.get("value", ""),
                "profile_url": entry.get("href", ""),
                "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp":   entry.get("timestamp", 0),
            })
    logger.info("[followers] 팔로워 %d명 파싱 완료", len(results))
    return results


def parse_following(data_dir):
    """following.json -> list of {username, profile_url, followed_at, timestamp}

    신버전 형식:
      {"relationships_following": [{"title": "username", "string_list_data": [{"href": "...", "timestamp": 123}]}]}
    구버전 형식 (string_list_data에 value 있음):
      {"relationships_following": [{"title": "", "string_list_data": [{"href": "...", "value": "username", "timestamp": 123}]}]}
    """
    raw = _load_json(os.path.join(data_dir, "following.json"), "following")
    if raw is None:
        return []

    if isinstance(raw, dict):
        for key in ("relationships_following", "following", "relationships_following_hashtags"):
            if key in raw and isinstance(raw[key], list):
                logger.debug("[following] JSON 키 사용: %r", key)
                raw = raw[key]
                break
        else:
            for k, v in raw.items():
                if isinstance(v, list):
                    logger.warning("[following] 알 수 없는 키 %r 사용 (전체 키: %s)", k, list(raw.keys()))
                    raw = v
                    break
            else:
                logger.error("[following] 파싱 실패 — 지원하지 않는 JSON 구조. 키: %s", list(raw.keys()))
                return []

    results = []
    for item in raw:
        # 신버전: username이 item["title"]에, 구버전: string_list_data[0]["value"]에 있음
        item_title = item.get("title", "")
        for entry in item.get("string_list_data", []):
            username = item_title or entry.get("value", "")
            results.append({
                "username":    username,
                "profile_url": entry.get("href", ""),
                "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp":   entry.get("timestamp", 0),
            })
    logger.info("[following] 팔로잉 %d명 파싱 완료", len(results))
    return results


def parse_liked_posts(data_dir):
    """liked_posts.json -> list of {username, post_url, liked_at, timestamp}

    신버전 형식 (최상위 배열):
      [{"timestamp": 123, "label_values": [
          {"label": "URL", "href": "...", "value": "..."},
          {"title": "소유자", "dict": [{"label": "사용자 이름", "value": "username"}, ...]}
      ]}]

    구버전 형식:
      {"likes_media_likes": [{"title": "username", "string_list_data": [{"href": "...", "timestamp": 123}]}]}
    """
    raw = _load_json(os.path.join(data_dir, "liked_posts.json"), "liked_posts")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("likes_media_likes", [])

    results = []
    for item in raw:
        if "label_values" in item:
            # 신버전: timestamp 최상위, label_values 배열에서 URL과 username 추출
            timestamp = item.get("timestamp", 0)
            post_url = ""
            username = ""

            for lv in item.get("label_values", []):
                if lv.get("label") == "URL":
                    post_url = lv.get("href") or lv.get("value", "")
                # 소유자(Owner) 항목에서 사용자 이름 추출
                if lv.get("dict") and not lv.get("label"):
                    for d in lv.get("dict", []):
                        d_label = _fix_str(d.get("label", ""))
                        if "사용자 이름" in d_label or d_label.lower() == "username":
                            username = d.get("value", "")
                            break

            results.append({
                "username":  username,
                "post_url":  post_url,
                "liked_at":  _ts_to_str(timestamp),
                "timestamp": timestamp,
            })
        else:
            # 구버전
            title = item.get("title", "")
            for entry in item.get("string_list_data", []):
                results.append({
                    "username":  title,
                    "post_url":  entry.get("href", ""),
                    "liked_at":  _ts_to_str(entry.get("timestamp", 0)),
                    "timestamp": entry.get("timestamp", 0),
                })
    logger.info("[liked_posts] 게시물 좋아요 %d건 파싱 완료", len(results))
    return results


def parse_liked_comments(data_dir):
    """liked_comments.json -> list of {username, post_url, liked_at, timestamp}

    형식: {"likes_comment_likes": [{"title": "username", "string_list_data": [{"href": "...", "value": "👍", "timestamp": 123}]}]}
    """
    raw = _load_json(os.path.join(data_dir, "liked_comments.json"), "liked_comments")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("likes_comment_likes", [])

    results = []
    for item in raw:
        title = item.get("title", "")
        for entry in item.get("string_list_data", []):
            results.append({
                "username": title,
                "post_url": entry.get("href", ""),
                "liked_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp": entry.get("timestamp", 0),
            })
    logger.info("[liked_comments] 댓글 좋아요 %d건 파싱 완료", len(results))
    return results


def parse_comments(data_dir):
    """post_comments_1.json -> list of {username, content, post_url, commented_at, timestamp}

    신버전 형식 (최상위 배열, string_map_data 사용):
      [{"string_map_data": {
          "Comment": {"value": "댓글 내용"},
          "Media Owner": {"value": "게시물 주인 username"},
          "Time": {"timestamp": 123}
      }}]

    구버전 형식:
      [{"title": "username", "string_list_data": [{"value": "댓글", "href": "...", "timestamp": 123}]}]
    또는 {"comments_media_comments": [...]}
    """
    raw = _load_json(os.path.join(data_dir, "post_comments_1.json"), "comments")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("comments_media_comments", [])

    results = []
    for item in raw:
        if "string_map_data" in item:
            # 신버전
            smd = item["string_map_data"]
            username = _fix_str(smd.get("Media Owner", {}).get("value", ""))
            content  = _fix_str(smd.get("Comment", {}).get("value", ""))
            timestamp = smd.get("Time", {}).get("timestamp", 0)
            results.append({
                "username":     username,
                "content":      content,
                "post_url":     "",
                "commented_at": _ts_to_str(timestamp),
                "timestamp":    timestamp,
            })
        else:
            # 구버전
            title = _fix_str(item.get("title", ""))
            for entry in item.get("string_list_data", []):
                results.append({
                    "username":     title,
                    "content":      _fix_str(entry.get("value", "")),
                    "post_url":     entry.get("href", ""),
                    "commented_at": _ts_to_str(entry.get("timestamp", 0)),
                    "timestamp":    entry.get("timestamp", 0),
                })
    logger.info("[comments] 댓글 %d건 파싱 완료", len(results))
    return results


def parse_recently_unfollowed(data_dir):
    """recently_unfollowed_profiles.json → 내가 최근 언팔한 계정 목록.

    신버전 형식 (최상위 배열):
      [{"timestamp": 123, "label_values": [
          {"label": "URL", "value": "..."},
          {"label": "이름", "value": "..."},
          {"label": "사용자 이름", "value": "username"}
      ]}]
    """
    raw = _load_json(os.path.join(data_dir, "recently_unfollowed_profiles.json"), "recently_unfollowed")
    if raw is None:
        return []

    items = raw if isinstance(raw, list) else [raw]
    results = []
    for item in items:
        username = ""
        profile_url = ""
        ts = item.get("timestamp", 0)

        for lv in item.get("label_values", []):
            label = _fix_str(lv.get("label", ""))
            val   = lv.get("value", "")
            if label in ("사용자 이름", "Username", "username"):
                username = val
            elif label == "URL" and val.startswith("http") and "instagram.com" in val:
                profile_url = val

        if not username:
            continue
        if not profile_url:
            profile_url = f"https://www.instagram.com/{username}/"
        results.append({
            "username":    username,
            "profile_url": profile_url,
            "followed_at": _ts_to_str(ts),
            "timestamp":   ts,
        })

    logger.info("[recently_unfollowed] 내가 언팔한 계정 %d명 파싱 완료", len(results))
    return results


def extract_zip(zip_path, extract_dir):
    """ZIP 파일에서 필요한 JSON 파일만 추출."""
    target_files = {
        "followers_1.json",
        "following.json",
        "liked_posts.json",
        "liked_comments.json",
        "post_comments_1.json",
        "recently_unfollowed_profiles.json",
    }
    found = {}
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info("[zip] 압축 해제 시작: %s (%.1f MB)", os.path.basename(zip_path), zip_size_mb)

    with zipfile.ZipFile(zip_path, "r") as zf:
        all_names = zf.namelist()
        logger.debug("[zip] ZIP 내부 항목 수: %d", len(all_names))

        for name in all_names:
            basename = os.path.basename(name)
            if basename in target_files and basename not in found:
                logger.info("[zip] 추출 중: %s", name)
                data = zf.read(name)
                dest = os.path.join(extract_dir, basename)
                with open(dest, "wb") as out:
                    out.write(data)
                found[basename] = dest
                logger.info("[zip] 추출 완료: %s (%.1f KB)", basename, len(data) / 1024)

    if not found:
        logger.warning(
            "[zip] 필요한 JSON 파일을 찾지 못했습니다. "
            "ZIP 내부 경로를 확인하세요. (찾는 파일: %s)", target_files
        )
    else:
        logger.info("[zip] 총 %d개 파일 추출 완료: %s", len(found), list(found.keys()))
    return found


def detect_dm_my_name(zip_path: str) -> str:
    """ZIP 내 DM 참가자 목록에서 가장 많이 등장하는 이름 = 내 표시 이름."""
    if not os.path.exists(zip_path):
        return ""
    name_freq: dict[str, int] = {}
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
                participants = [_fix_str(p.get("name", ""))
                                for p in data.get("participants", [])]
                others = [p for p in participants if p != my_name]
                other_party = others[0] if others else thread_title

                for msg in data.get("messages", []):
                    sender = _fix_str(msg.get("sender_name", ""))
                    ts_ms  = msg.get("timestamp_ms", 0)
                    ts     = ts_ms // 1000
                    content = _fix_str(msg.get("content", ""))
                    occurred = _ts_to_str(ts)

                    # 내가 보낸 메시지/공유/좋아요
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

                    # 내가 한 이모지 반응
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


def get_data_summary(data_dir):
    """업로드된 파일 현황 반환."""
    files = [
        "followers_1.json",
        "following.json",
        "liked_posts.json",
        "liked_comments.json",
        "post_comments_1.json",
        "recently_unfollowed_profiles.json",
    ]
    return {f: os.path.exists(os.path.join(data_dir, f)) for f in files}
