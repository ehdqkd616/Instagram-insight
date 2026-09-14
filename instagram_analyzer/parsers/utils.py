import json
import logging
import os
import re
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger("instagram_analyzer.parsers")


def _ts_to_str(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _fix_str(s: str) -> str:
    """Instagram이 한글을 Latin-1 mojibake로 내보낸 경우 UTF-8로 복원."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _username_from_href(href: str) -> str:
    """https://www.instagram.com/<username>/ 형태의 URL에서 실제 계정 핸들만 추출."""
    try:
        path = urlparse(href).path
    except Exception:
        return ""
    return path.strip("/").split("/")[-1] if path else ""


def _load_json(path: str, label: str):
    if not os.path.exists(path):
        logger.debug("[%s] 파일 없음: %s", label, path)
        return None
    size_kb = os.path.getsize(path) / 1024
    logger.debug("[%s] 파싱 시작 (%.1f KB): %s", label, size_kb, os.path.basename(path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.debug("[%s] 파싱 완료", label)
    return data


def _load_numbered_json_files(data_dir: str, prefix: str, label: str) -> list:
    """followers_1.json, followers_2.json, ... 처럼 인스타그램이 항목 수가 많을 때
    번호를 붙여 여러 파일로 쪼개 내보내는 JSON들을 모두 찾아 순서대로 로드한다.
    각 파일의 원본 JSON(raw)을 리스트로 반환하며, 배열/딕셔너리 해석은 호출자가 담당한다."""
    if not os.path.isdir(data_dir):
        return []

    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\.json$")
    numbered = []
    for name in os.listdir(data_dir):
        m = pattern.match(name)
        if m:
            numbered.append((int(m.group(1)), name))
    numbered.sort(key=lambda x: x[0])

    raws = []
    for _, name in numbered:
        data = _load_json(os.path.join(data_dir, name), label)
        if data is not None:
            raws.append(data)
    return raws
