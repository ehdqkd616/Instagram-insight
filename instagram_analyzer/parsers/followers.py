import logging
import os

from parsers.utils import (
    _fix_str, _load_json, _load_numbered_json_files, _ts_to_str, _username_from_href,
)

logger = logging.getLogger("instagram_analyzer.parsers.followers")


def parse_followers(data_dir: str) -> list:
    # 팔로워가 많으면 followers_1.json, followers_2.json, ... 으로 나뉘어 내보내진다.
    raws = _load_numbered_json_files(data_dir, "followers_", "followers")
    if not raws:
        return []

    results = []
    for raw in raws:
        for item in raw:
            for entry in item.get("string_list_data", []):
                href = entry.get("href", "")
                # value가 실명/닉네임으로 깨져 나오는 경우가 있어, URL의 실제 계정 핸들을 우선한다.
                username = _username_from_href(href) or _fix_str(entry.get("value", ""))
                results.append({
                    "username":    username,
                    "profile_url": href,
                    "followed_at": _ts_to_str(entry.get("timestamp", 0)),
                    "timestamp":   entry.get("timestamp", 0),
                })
    logger.info("[followers] 팔로워 %d명 파싱 완료 (파일 %d개)", len(results), len(raws))
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
            href = entry.get("href", "")
            # title은 실명/닉네임(한글 등 mojibake 포함 가능)인 경우가 있어
            # 실제 계정 핸들인 URL과 value를 우선 사용한다.
            username = (
                _username_from_href(href)
                or _fix_str(entry.get("value", ""))
                or _fix_str(item_title)
            )
            results.append({
                "username":    username,
                "profile_url": href,
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

        # value가 실명/닉네임으로 깨져 나오는 경우가 있어, URL의 실제 계정 핸들을 우선한다.
        username = _username_from_href(profile_url) or _fix_str(username)
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
