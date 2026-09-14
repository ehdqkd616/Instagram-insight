import logging
import os
import re
import zipfile

logger = logging.getLogger("instagram_analyzer.parsers.zip")

_TARGET_FILES = {
    "followers_1.json",
    "following.json",
    "liked_posts.json",
    "liked_comments.json",
    "post_comments_1.json",
    "recently_unfollowed_profiles.json",
}

# 팔로워/댓글이 많으면 인스타그램이 followers_1.json, followers_2.json, ...
# 식으로 파일을 여러 개로 쪼개서 내보낸다. 번호가 붙은 파일도 모두 추출해야 한다.
_NUMBERED_PATTERNS = (
    re.compile(r"^followers_\d+\.json$"),
    re.compile(r"^post_comments_\d+\.json$"),
)


def _is_target(basename: str) -> bool:
    if basename in _TARGET_FILES:
        return True
    return any(p.match(basename) for p in _NUMBERED_PATTERNS)


def _is_threads_path(name: str) -> bool:
    """Threads 계정 데이터는 인스타그램 내보내기 zip에 threads_and_instagram 같은
    폴더로 같이 담겨오는데, 여기 들어있는 followers_1.json / following.json 등은
    인스타그램이 아닌 스레드 관계 데이터라서 절대 사용하면 안 된다."""
    return "thread" in name.lower()


def extract_zip(zip_path: str, extract_dir: str) -> dict:
    """ZIP 파일에서 필요한 JSON 파일만 추출. 스레드(Threads) 관련 폴더는 제외한다."""
    found = {}
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info("[zip] 압축 해제 시작: %s (%.1f MB)", os.path.basename(zip_path), zip_size_mb)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if _is_threads_path(name):
                logger.debug("[zip] 스레드 데이터 제외: %s", name)
                continue
            basename = os.path.basename(name)
            if _is_target(basename) and basename not in found:
                logger.info("[zip] 추출 중: %s", name)
                data = zf.read(name)
                dest = os.path.join(extract_dir, basename)
                with open(dest, "wb") as out:
                    out.write(data)
                found[basename] = dest
                logger.info("[zip] 추출 완료: %s (%.1f KB)", basename, len(data) / 1024)

    if not found:
        logger.warning("[zip] 필요한 JSON 파일을 찾지 못했습니다. (찾는 파일: %s)", _TARGET_FILES)
    else:
        logger.info("[zip] 총 %d개 파일 추출 완료: %s", len(found), list(found.keys()))
    return found


def get_data_summary(data_dir: str) -> dict:
    """업로드된 파일 현황 반환."""
    return {f: os.path.exists(os.path.join(data_dir, f)) for f in _TARGET_FILES}
