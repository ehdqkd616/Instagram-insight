import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from db import (
    admin_update_user, create_user, find_user_by_username, list_users,
    get_security_question, set_security_qa, verify_security_answer,
)

bp = Blueprint("auth", __name__)
logger = logging.getLogger("instagram_analyzer.auth")

SECURITY_QUESTIONS = [
    "어린 시절 주로 살던 동네 이름은?",
    "나의 첫 번째 반려동물 이름은?",
    "다닌 초등학교 이름은?",
    "가장 좋아하는 음식은?",
    "어머니의 성함(이름)은?",
    "가장 친한 친구의 이름은?",
    "나의 보물 1호는?",
]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = find_user_by_username(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            logger.info("로그인 성공: user_id=%d username=%r", user.id, user.username)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        logger.warning("로그인 실패: username=%r", username)
        flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")

    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username     = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm", "")
        sec_q        = request.form.get("security_question", "").strip()
        sec_a        = request.form.get("security_answer", "").strip()

        error = None
        if not username or not password:
            error = "아이디와 비밀번호를 입력해주세요."
        elif len(username) < 3:
            error = "아이디는 3자 이상이어야 합니다."
        elif len(password) < 6:
            error = "비밀번호는 6자 이상이어야 합니다."
        elif password != confirm:
            error = "비밀번호가 일치하지 않습니다."
        elif not sec_q or not sec_a:
            error = "비밀번호 찾기를 위해 보안 질문과 답을 입력해주세요."

        if error:
            flash(error, "danger")
        else:
            user = create_user(username, password, display_name)
            if user is None:
                flash("이미 사용 중인 아이디입니다.", "danger")
            else:
                set_security_qa(user.id, sec_q, sec_a)
                flash("회원가입이 완료됐습니다. 로그인해주세요.", "success")
                return redirect(url_for("auth.login"))

    return render_template("register.html", security_questions=SECURITY_QUESTIONS)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    
    question = get_security_question(current_user.id)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "profile":
            display_name = request.form.get("display_name", "").strip()
            admin_update_user(current_user.id, display_name=display_name or None)
            flash("표시 이름이 변경됐습니다.", "success")

        elif action == "password":
            current_pw = request.form.get("current_password", "")
            new_pw     = request.form.get("new_password", "")
            confirm    = request.form.get("confirm", "")
            if not current_user.check_password(current_pw):
                flash("현재 비밀번호가 올바르지 않습니다.", "danger")
            elif len(new_pw) < 6:
                flash("새 비밀번호는 6자 이상이어야 합니다.", "danger")
            elif new_pw != confirm:
                flash("새 비밀번호가 일치하지 않습니다.", "danger")
            else:
                admin_update_user(current_user.id, new_password=new_pw)
                flash("비밀번호가 변경됐습니다.", "success")

        elif action == "security":
            sec_q = request.form.get("security_question", "").strip()
            sec_a = request.form.get("security_answer", "").strip()
            if not sec_q or not sec_a:
                flash("보안 질문과 답을 모두 입력해주세요.", "danger")
            else:
                set_security_qa(current_user.id, sec_q, sec_a)
                flash("보안 질문이 설정됐습니다.", "success")
                question = sec_q

        return redirect(url_for("auth.settings"))

    return render_template("settings.html",
                           security_questions=SECURITY_QUESTIONS,
                           current_question=question)


@bp.route("/logout")
@login_required
def logout():
    logger.info("로그아웃: user_id=%d username=%r", current_user.id, current_user.username)
    logout_user()
    flash("로그아웃됐습니다.", "info")
    return redirect(url_for("auth.login"))


# ── 아이디 찾기 ───────────────────────────────────────────────────────────────

@bp.route("/find-id")
def find_id():
    users = list_users()
    accounts = [{"username": u.username, "display_name": u.display_name} for u in users]
    return render_template("find_account.html", step="find_id", accounts=accounts)


# ── 비밀번호 찾기 (3단계) ─────────────────────────────────────────────────────

@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    # Step 1: 아이디 입력
    return render_template("find_account.html", step="pw_step1")


@bp.route("/forgot-password/verify", methods=["POST"])
def forgot_password_verify():
    # Step 2: 보안 질문 확인
    username = request.form.get("username", "").strip()
    user = find_user_by_username(username)
    if not user:
        flash("존재하지 않는 아이디입니다.", "danger")
        return redirect(url_for("auth.forgot_password"))

    question = get_security_question(user.id)
    if not question:
        flash("보안 질문이 설정되어 있지 않습니다. 관리자에게 비밀번호 초기화를 요청하세요.", "warning")
        return redirect(url_for("auth.forgot_password"))

    session["recovery_uid"] = user.id
    session["recovery_username"] = user.username
    return render_template("find_account.html", step="pw_step2",
                           username=username, question=question)


@bp.route("/forgot-password/answer", methods=["POST"])
def forgot_password_answer():
    # Step 3: 답 검증 후 새 비밀번호 설정
    uid = session.get("recovery_uid")
    username = session.get("recovery_username", "")
    if not uid:
        return redirect(url_for("auth.forgot_password"))

    answer = request.form.get("answer", "")
    if not verify_security_answer(uid, answer):
        flash("보안 질문의 답이 올바르지 않습니다.", "danger")
        question = get_security_question(uid)
        return render_template("find_account.html", step="pw_step2",
                               username=username, question=question)

    session["recovery_verified"] = True
    return render_template("find_account.html", step="pw_step3", username=username)


@bp.route("/forgot-password/reset", methods=["POST"])
def forgot_password_reset():
    # 비밀번호 변경
    if not session.get("recovery_verified"):
        return redirect(url_for("auth.forgot_password"))

    uid = session.get("recovery_uid")
    username = session.get("recovery_username", "")
    new_pw  = request.form.get("new_password", "")
    confirm = request.form.get("confirm", "")

    if len(new_pw) < 6:
        flash("비밀번호는 6자 이상이어야 합니다.", "danger")
        return render_template("find_account.html", step="pw_step3", username=username)
    if new_pw != confirm:
        flash("비밀번호가 일치하지 않습니다.", "danger")
        return render_template("find_account.html", step="pw_step3", username=username)

    admin_update_user(uid, new_password=new_pw)
    session.pop("recovery_uid", None)
    session.pop("recovery_username", None)
    session.pop("recovery_verified", None)
    logger.info("비밀번호 재설정 완료: user_id=%d", uid)
    flash("비밀번호가 변경됐습니다. 로그인하세요.", "success")
    return redirect(url_for("auth.login"))
