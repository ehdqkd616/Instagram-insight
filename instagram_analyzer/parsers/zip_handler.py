import logging
import os
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


def extract_zip(zip_path: str, extract_dir: str) -> dict:
    """ZIP 파일에서 필요한 JSON 파일만 추출."""
    found = {}
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info("[zip] 압축 해제 시작: %s (%.1f MB)", os.path.basename(zip_path), zip_size_mb)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            basename = os.path.basename(name)
            if basename in _TARGET_FILES and basename not in found:
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
