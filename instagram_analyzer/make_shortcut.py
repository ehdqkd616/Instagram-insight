"""
Instagram Analyzer — 바탕화면 바로가기 생성기
instagram_analyzer/ 폴더에서 python make_shortcut.py 로 실행하세요.
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path

BASE_DIR  = Path(__file__).parent          # = instagram_analyzer/
LAUNCHER  = BASE_DIR / "launcher.py"
ICON      = BASE_DIR / "icon.ico"
DESKTOP   = Path(os.path.expanduser("~")) / "Desktop"
SHORTCUT  = DESKTOP / "Instagram Analyzer.lnk"

# 현재 실행 중인 Python 옆에 있는 pythonw.exe 사용 (콘솔 창 없음)
pythonw = Path(sys.executable).parent / "pythonw.exe"
if not pythonw.exists():
    pythonw = Path(sys.executable).parent.parent / "bin" / "pythonw.exe"
if not pythonw.exists():
    print(f"[오류] pythonw.exe 를 찾을 수 없습니다: {pythonw}")
    print("python.exe 경로:", sys.executable)
    input("Enter 키를 눌러 종료...")
    sys.exit(1)

print(f"Python  : {sys.executable}")
print(f"pythonw : {pythonw}")
print(f"런처    : {LAUNCHER}")
print(f"아이콘  : {ICON}")
print(f"바로가기: {SHORTCUT}")
print()

icon_line = f'lnk.IconLocation = "{ICON},0"' if ICON.exists() else ""

q = '"'
vbs = (
    'Set sh  = CreateObject("WScript.Shell")\n'
    f'Set lnk = sh.CreateShortcut("{SHORTCUT}")\n'
    f'lnk.TargetPath       = "{pythonw}"\n'
    f'lnk.Arguments        = {q}{q}{q}{LAUNCHER}{q}{q}{q}\n'
    f'lnk.WorkingDirectory = "{BASE_DIR}"\n'
    'lnk.Description      = "Instagram Analyzer"\n'
    'lnk.WindowStyle      = 1\n'
    + (icon_line + "\n" if icon_line else "")
    + "lnk.Save\n"
)

with tempfile.NamedTemporaryFile(mode="w", suffix=".vbs",
                                  delete=False, encoding="ascii") as f:
    f.write(vbs)
    tmp = f.name

try:
    subprocess.run(["wscript.exe", tmp], check=True)
    print("Shortcut created successfully on Desktop!")
    print("Double-click 'Instagram Analyzer' on your Desktop to launch.")
except subprocess.CalledProcessError as e:
    print(f"[오류] 바로가기 생성 실패: {e}")
finally:
    os.unlink(tmp)

try:
    input("\nEnter 키를 눌러 창 닫기...")
except EOFError:
    pass
