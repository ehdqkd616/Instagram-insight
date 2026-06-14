import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from config import DATA_DIR, UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS
from services.parser import extract_zip, get_data_summary
from services.follower_service import get_stats


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.config["DATA_DIR"] = DATA_DIR
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    os.makedirs(DATA_DIR, exist_ok=True)

    from routes.followers import bp as followers_bp
    from routes.activity import bp as activity_bp
    app.register_blueprint(followers_bp)
    app.register_blueprint(activity_bp)

    @app.route("/")
    def index():
        summary = get_data_summary(DATA_DIR)
        has_data = any(summary.values())
        stats = get_stats(DATA_DIR) if has_data else None
        return render_template("index.html", summary=summary, has_data=has_data, stats=stats)

    @app.route("/upload", methods=["POST"])
    def upload():
        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            flash("파일을 선택해주세요.", "danger")
            return redirect(url_for("index"))

        uploaded = []
        for file in files:
            if file.filename == "":
                continue
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"{file.filename}: 지원하지 않는 파일 형식입니다. (json 또는 zip만 가능)", "danger")
                continue

            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            if ext == "zip":
                try:
                    found = extract_zip(save_path, DATA_DIR)
                    os.remove(save_path)
                    uploaded.extend(found.keys())
                except Exception as e:
                    flash(f"ZIP 해제 실패: {e}", "danger")
            else:
                uploaded.append(filename)

        if uploaded:
            flash(f"업로드 완료: {', '.join(uploaded)}", "success")
        return redirect(url_for("index"))

    @app.route("/delete-data", methods=["POST"])
    def delete_data():
        import glob
        for f in glob.glob(os.path.join(DATA_DIR, "*.json")):
            os.remove(f)
        flash("데이터가 삭제되었습니다.", "info")
        return redirect(url_for("index"))

    @app.route("/api/data-summary")
    def api_data_summary():
        return jsonify(get_data_summary(DATA_DIR))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)
