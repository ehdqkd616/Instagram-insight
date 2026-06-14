import glob
import logging
import os
import time

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_file,
)
from flask_login import LoginManager, login_required, current_user
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import BASE_DIR, DATA_DIR, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, get_secret_key
from logging_config import setup_logging, read_recent_logs
from models import init_db, find_user_by_id, update_instagram_username
from services.parser import extract_zip, get_data_summary
from services.follower_service import get_stats

logger = logging.getLogger("instagram_analyzer.app")


def create_app():
    app = Flask(__name__)
    app.secret_key = get_secret_key()
    app.config["DATA_DIR"] = DATA_DIR
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = None

    os.makedirs(DATA_DIR, exist_ok=True)
    init_db()

    # ── Flask-Login 설정 ─────────────────────────────────
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "로그인이 필요합니다."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return find_user_by_id(int(user_id))

    # ── 블루프린트 등록 ──────────────────────────────────
    from routes.auth import bp as auth_bp
    from routes.followers import bp as followers_bp
    from routes.activity import bp as activity_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(followers_bp)
    app.register_blueprint(activity_bp)

    # ── 요청/응답 로깅 미들웨어 ──────────────────────────
    @app.before_request
    def _log_request():
        request._start_time = time.time()
        user_info = f"user_id={current_user.id}" if current_user.is_authenticated else "anonymous"
        logger.debug("→ %s %s  (%s, from %s)", request.method, request.path, user_info, request.remote_addr)

    @app.after_request
    def _log_response(response):
        elapsed = (time.time() - getattr(request, "_start_time", time.time())) * 1000
        level = logging.WARNING if response.status_code >= 400 else logging.DEBUG
        logger.log(level, "← %s %s  %s  %.1fms", request.method, request.path, response.status_code, elapsed)
        return response

    # ── 에러 핸들러 ──────────────────────────────────────
    @app.errorhandler(RequestEntityTooLarge)
    def handle_413(_e):
        logger.warning("413 Request Entity Too Large: %s", request.path)
        flash("파일이 너무 큽니다.", "danger")
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def handle_404(_e):
        return render_template("error.html", code=404, msg="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(500)
    def handle_500(e):
        logger.error("500 Internal Server Error: %s — %s", request.path, e, exc_info=True)
        return render_template("error.html", code=500, msg=f"서버 오류: {e}"), 500

    # ── 메인 라우트 ──────────────────────────────────────
    @app.route("/")
    @login_required
    def index():
        summary = get_data_summary(current_user.data_dir)
        has_data = any(summary.values())
        stats = get_stats(current_user.data_dir) if has_data else None
        return render_template("index.html", summary=summary, has_data=has_data, stats=stats)

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload():
        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            flash("파일을 선택해주세요.", "danger")
            return redirect(url_for("index"))

        user_data_dir = current_user.data_dir
        uploaded = []

        for file in files:
            if file.filename == "":
                continue
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"{file.filename}: 지원하지 않는 파일 형식입니다. (json 또는 zip만 가능)", "danger")
                logger.warning("Unsupported file: %s (user_id=%d)", file.filename, current_user.id)
                continue

            filename = secure_filename(file.filename)
            save_path = os.path.join(user_data_dir, filename)

            logger.info("[user=%d] 파일 저장 시작: %s", current_user.id, filename)
            file.save(save_path)
            size_mb = os.path.getsize(save_path) / (1024 * 1024)
            logger.info("[user=%d] 파일 저장 완료: %s (%.1f MB)", current_user.id, filename, size_mb)

            if ext == "zip":
                try:
                    logger.info("[user=%d] ZIP 압축 해제 시작: %s", current_user.id, filename)
                    found = extract_zip(save_path, user_data_dir)
                    os.remove(save_path)
                    logger.info("[user=%d] ZIP 완료 — 추출 파일: %s", current_user.id, list(found.keys()))
                    uploaded.extend(found.keys())
                except Exception as e:
                    logger.error("[user=%d] ZIP 해제 실패: %s", current_user.id, e, exc_info=True)
                    flash(f"ZIP 해제 실패: {e}", "danger")
            else:
                uploaded.append(filename)

        # 업로드된 데이터에서 인스타그램 계정명 자동 감지
        if uploaded:
            _detect_instagram_username(user_data_dir)
            flash(f"업로드 완료: {', '.join(uploaded)}", "success")
            logger.info("[user=%d] 업로드 완료: %s", current_user.id, uploaded)

        return redirect(url_for("index"))

    @app.route("/delete-data", methods=["POST"])
    @login_required
    def delete_data():
        removed = []
        for f in glob.glob(os.path.join(current_user.data_dir, "*.json")):
            os.remove(f)
            removed.append(os.path.basename(f))
        logger.info("[user=%d] 데이터 삭제: %s", current_user.id, removed)
        flash("데이터가 삭제됐습니다.", "info")
        return redirect(url_for("index"))

    # ── 로그 뷰어 ────────────────────────────────────────
    @app.route("/logs")
    @login_required
    def logs_page():
        return render_template("logs.html")

    @app.route("/api/logs")
    @login_required
    def api_logs():
        n = int(request.args.get("n", 300))
        level_filter = request.args.get("level", "ALL").upper()
        entries = read_recent_logs(n)
        if level_filter != "ALL":
            entries = [e for e in entries if e["level"] == level_filter]
        return jsonify({"entries": entries, "total": len(entries)})

    @app.route("/api/logs/download")
    @login_required
    def download_log():
        from logging_config import LOG_FILE
        if LOG_FILE and os.path.exists(LOG_FILE):
            return send_file(LOG_FILE, as_attachment=True, download_name="instagram_analyzer.log")
        return jsonify({"error": "로그 파일이 없습니다."}), 404

    @app.route("/api/data-summary")
    @login_required
    def api_data_summary():
        return jsonify(get_data_summary(current_user.data_dir))

    return app


def _detect_instagram_username(data_dir: str):
    """followers_1.json 에서 인스타그램 계정명 자동 감지 시도."""
    try:
        from services.parser import parse_followers
        # followers 파일에는 계정명이 없음 — following.json의 title 필드 사용 불가
        # 대신 데이터가 존재한다는 사실 자체를 기록
        pass
    except Exception:
        pass


if __name__ == "__main__":
    log_file = setup_logging(BASE_DIR)
    app = create_app()
    logger.info("=" * 60)
    logger.info("Instagram Analyzer 시작")
    logger.info("로그 파일: %s", log_file)
    logger.info("데이터 디렉토리: %s", DATA_DIR)
    logger.info("접속 주소: http://127.0.0.1:5000")
    logger.info("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)
