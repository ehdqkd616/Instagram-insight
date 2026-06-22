"""
Instagram Analyzer — 비밀번호 긴급 초기화 도구
python reset_password.py 로 실행하세요.
"""
import sys
sys.path.insert(0, "instagram_analyzer")
sys.stdout.reconfigure(encoding="utf-8")

from models import init_db, list_users, admin_update_user

init_db()
users = list_users()

print("=" * 50)
print("  Instagram Analyzer — 계정 복구 도구")
print("=" * 50)
print()
print("등록된 계정 목록:")
for u in users:
    admin_mark = " [관리자]" if u.is_admin else ""
    print(f"  ID={u.id}  아이디: {u.username}  ({u.display_name}){admin_mark}")

print()
try:
    user_id = int(input("초기화할 계정 ID 입력: ").strip())
except ValueError:
    print("[오류] 숫자를 입력하세요.")
    input("Enter 키를 눌러 종료...")
    sys.exit(1)

target = next((u for u in users if u.id == user_id), None)
if target is None:
    print("[오류] 해당 ID의 계정이 없습니다.")
    input("Enter 키를 눌러 종료...")
    sys.exit(1)

print(f"선택된 계정: {target.username} ({target.display_name})")
new_pw = input("새 비밀번호 (6자 이상): ").strip()

if len(new_pw) < 6:
    print("[오류] 비밀번호는 6자 이상이어야 합니다.")
    input("Enter 키를 눌러 종료...")
    sys.exit(1)

admin_update_user(user_id, new_password=new_pw)
print()
print(f"완료! '{target.username}' 계정의 비밀번호가 초기화됐습니다.")
print(f"이제 아이디 '{target.username}' / 새 비밀번호로 로그인하세요.")
print()
input("Enter 키를 눌러 종료...")
