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
    """followers_1.json -> list of {username, profile_url, followed_at, timestamp}"""
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

    Instagram 내보내기 버전에 따라 JSON 구조가 다를 수 있어 여러 형식을 처리.
    - 신버전: {"relationships_following": [...]}
    - 구버전: [...]
    - 일부 버전: {"following": [...]}  또는 단일 dict 감싸기
    """
    raw = _load_json(os.path.join(data_dir, "following.json"), "following")
    if raw is None:
        return []

    if isinstance(raw, dict):
        # 알려진 키 순서대로 시도
        for key in ("relationships_following", "following", "relationships_following_hashtags"):
            if key in raw and isinstance(raw[key], list):
                logger.debug("[following] JSON 키 사용: %r", key)
                raw = raw[key]
                break
        else:
            # 키를 모르면 첫 번째 리스트 값 사용
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
        for entry in item.get("string_list_data", []):
            results.append({
                "username":    entry.get("value", ""),
                "profile_url": entry.get("href", ""),
                "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp":   entry.get("timestamp", 0),
            })
    logger.info("[following] 팔로잉 %d명 파싱 완료", len(results))
    return results


def parse_liked_posts(data_dir):
    """liked_posts.json -> list of {username, post_url, liked_at, timestamp}"""
    raw = _load_json(os.path.join(data_dir, "liked_posts.json"), "liked_posts")
    if raw is None:
        return []

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
    logger.info("[liked_posts] 게시물 좋아요 %d건 파싱 완료", len(results))
    return results


def parse_liked_comments(data_dir):
    """liked_comments.json -> list of {username, post_url, liked_at, timestamp}"""
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
    """post_comments_1.json -> list of {username, content, post_url, commented_at, timestamp}"""
    raw = _load_json(os.path.join(data_dir, "post_comments_1.json"), "comments")
    if raw is None:
        return []

    if isinstance(raw, dict):
        raw = raw.get("comments_media_comments", [])

    results = []
    for item in raw:
        title = item.get("title", "")
        for entry in item.get("string_list_data", []):
            results.append({
                "username":     title,
                "content":      entry.get("value", ""),
                "post_url":     entry.get("href", ""),
                "commented_at": _ts_to_str(entry.get("timestamp", 0)),
                "timestamp":    entry.get("timestamp", 0),
            })
    logger.info("[comments] 댓글 %d건 파싱 완료", len(results))
    return results


def extract_zip(zip_path, extract_dir):
    """ZIP 파일에서 필요한 JSON 파일만 추출."""
    target_files = {
        "followers_1.json",
        "following.json",
        "liked_posts.json",
        "liked_comments.json",
        "post_comments_1.json",
    }
    found = {}
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info("[zip] 압축 해제 시작: %s (%.1f MB)", os.path.basename(zip_path), zip_size_mb)

    with zipfile.ZipFile(zip_path, "r") as zf:
        all_names = zf.namelist()
        logger.debug("[zip] ZIP 내부 항목 수: %d", len(all_names))

        for name in all_names:
            basename = os.path.basename(name)
            if basename in target_files:
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
