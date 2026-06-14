import json
import zipfile
import os
from datetime import datetime


def _ts_to_str(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def parse_followers(data_dir):
    """followers_1.json -> list of {username, profile_url, followed_at, timestamp}"""
    path = os.path.join(data_dir, "followers_1.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    results = []
    for item in raw:
        for entry in item.get("string_list_data", []):
            results.append({
                "username": entry.get("value", ""),
                "profile_url": entry.get("href", ""),
                "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp": entry.get("timestamp", 0),
            })
    return results


def parse_following(data_dir):
    """following.json -> list of {username, profile_url, followed_at, timestamp}"""
    path = os.path.join(data_dir, "following.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # following.json may have a top-level key "relationships_following"
    if isinstance(raw, dict):
        raw = raw.get("relationships_following", [])

    results = []
    for item in raw:
        for entry in item.get("string_list_data", []):
            results.append({
                "username": entry.get("value", ""),
                "profile_url": entry.get("href", ""),
                "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp": entry.get("timestamp", 0),
            })
    return results


def parse_liked_posts(data_dir):
    """liked_posts.json -> list of {username, post_url, liked_at, timestamp}"""
    path = os.path.join(data_dir, "liked_posts.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # May be wrapped under a key
    if isinstance(raw, dict):
        raw = raw.get("likes_media_likes", [])

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
    return results


def parse_liked_comments(data_dir):
    """liked_comments.json -> list of {username, post_url, liked_at, timestamp}"""
    path = os.path.join(data_dir, "liked_comments.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

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
    return results


def parse_comments(data_dir):
    """post_comments_1.json -> list of {username, content, post_url, commented_at, timestamp}"""
    path = os.path.join(data_dir, "post_comments_1.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        raw = raw.get("comments_media_comments", [])

    results = []
    for item in raw:
        title = item.get("title", "")
        for entry in item.get("string_list_data", []):
            results.append({
                "username": title,
                "content": entry.get("value", ""),
                "post_url": entry.get("href", ""),
                "commented_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp": entry.get("timestamp", 0),
            })
    return results


def extract_zip(zip_path, extract_dir):
    """ZIP 파일을 extract_dir 에 해제하고 JSON 파일들을 data_dir 로 복사."""
    target_files = {
        "followers_1.json",
        "following.json",
        "liked_posts.json",
        "liked_comments.json",
        "post_comments_1.json",
    }
    found = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            basename = os.path.basename(name)
            if basename in target_files:
                data = zf.read(name)
                dest = os.path.join(extract_dir, basename)
                with open(dest, "wb") as out:
                    out.write(data)
                found[basename] = dest
    return found


def get_data_summary(data_dir):
    """업로드된 파일 현황 반환."""
    files = [
        "followers_1.json",
        "following.json",
        "liked_posts.json",
        "liked_comments.json",
        "post_comments_1.json",
    ]
    return {f: os.path.exists(os.path.join(data_dir, f)) for f in files}
