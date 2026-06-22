import logging
import os

from parsers.utils import _fix_str, _load_json, _ts_to_str

logger = logging.getLogger("instagram_analyzer.parsers.followers")


def parse_followers(data_dir: str) -> list:
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


def parse_following(data_dir: str) -> list:
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
                    logger.warning("[following] 알 수 없는 키 %r 사용", k)
                    raw = v
                    break
            else:
                logger.error("[following] 파싱 실패 — 지원하지 않는 JSON 구조. 키: %s", list(raw.keys()))
                return []

    results = []
    for item in raw:
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


def parse_recently_unfollowed(data_dir: str) -> list:
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
