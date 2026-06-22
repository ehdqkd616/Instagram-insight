#!/usr/bin/env python3
"""
Instagram Analyzer — Windows Launcher
트레이 아이콘 + 서버 제어 + 실시간 로그 뷰어
"""
import datetime
import os
import socket
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "logs" / "app.log"
ICON_FILE = BASE_DIR / "icon.ico"
APP_URL = "http://127.0.0.1:5000"
PYTHON = sys.executable

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


# ── 아이콘 생성 ───────────────────────────────────────────────────────────────

def _make_icon_img(size: int = 64) -> "Image":
    """인스타그램 그라디언트 스타일 아이콘을 PIL로 생성."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 3색 그라디언트 배경
    stops = [(225, 48, 108), (193, 53, 132), (131, 58, 180)]
    n = len(stops) - 1
    for y in range(size):
        t = y / (size - 1)
        seg = min(int(t * n), n - 1)
        lt = t * n - seg
        r = int(stops[seg][0] * (1 - lt) + stops[seg + 1][0] * lt)
        g = int(stops[seg][1] * (1 - lt) + stops[seg + 1][1] * lt)
        b = int(stops[seg][2] * (1 - lt) + stops[seg + 1][2] * lt)
        draw.line([(0, y), (size - 1, y)], fill=(r, g, b, 255))

    # 둥근 마스크
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=size // 5, fill=255
    )
    img.putalpha(mask)

    # 카메라 아이콘 그리기
    d = ImageDraw.Draw(img)
    lw = max(2, size // 32)
    bw, bh = int(size * 0.54), int(size * 0.40)
    bx, by = (size - bw) // 2, (size - bh) // 2 + size // 14
    d.rounded_rectangle([(bx, by), (bx + bw, by + bh)],
                         radius=size // 10, outline="white", width=lw)
    lr = bh // 3
    cx, cy = size // 2, size // 2 + size // 14
    d.ellipse([(cx - lr, cy - lr), (cx + lr, cy + lr)], outline="white", width=lw)
    bpw = bw // 4
    d.rectangle([(size // 2 - bpw // 2, by - lw - 1),
                  (size // 2 + bpw // 2, by + 1)], fill="white")
    dot = size // 18
    d.ellipse([(bx + size // 9, by + size // 20),
                (bx + size // 9 + dot, by + size // 20 + dot)], fill="white")
    return img


def _save_icon():
    """icon.ico 파일 저장 (바로가기용). Pillow 필요."""
    if ICON_FILE.exists():
        return
    try:
        from PIL import Image
        imgs = [_make_icon_img(s) for s in (256, 64, 48, 32, 16)]
        imgs[0].save(str(ICON_FILE), format="ICO",
                     sizes=[(s, s) for s in (256, 64, 48, 32, 16)],
                     append_images=imgs[1:])
    except Exception:
        pass


# ── 서버 관리 ─────────────────────────────────────────────────────────────────

class ServerManager:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def is_port_open(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
                return True
        except OSError:
            return False

    def start(self) -> bool:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return False
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            self._proc = subprocess.Popen(
                [PYTHON, str(BASE_DIR / "app.py")],
                cwd=str(BASE_DIR),
                env=env,
                creationflags=flags,
            )
            return True

    def stop(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None


# ── 메인 GUI ──────────────────────────────────────────────────────────────────

class LauncherApp:
    # 색상 팔레트
    IG_PINK   = "#E1306C"
    BG        = "#0d1117"
    BG2       = "#161b22"
    BG3       = "#21262d"
    FG        = "#e6edf3"
    FG2       = "#8b949e"
    GREEN     = "#3fb950"
    RED       = "#f85149"
    YELLOW    = "#d29922"
    BLUE      = "#58a6ff"

    LEVEL_COLOR = {
        "DEBUG":    "#8b949e",
        "INFO":     "#58a6ff",
        "WARNING":  "#d29922",
        "ERROR":    "#f85149",
        "CRITICAL": "#d2a8ff",
    }

    def __init__(self):
        self.server = ServerManager()
        self._log_pos = 0
        self._tray: "pystray.Icon | None" = None
        self._icon_img = None

        if HAS_TRAY:
            try:
                self._icon_img = _make_icon_img(64)
                _save_icon()
            except Exception:
                pass

        self._build_window()
        self._build_tray()

        # 앱 시작 시 서버 자동 시작
        self._do_start()
        self._poll_status()
        self._seek_log_end()
        self._tail_log()

    # ── 윈도우 구성 ──────────────────────────────────────────────────────────

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Instagram Analyzer")
        self.root.geometry("820x580")
        self.root.minsize(680, 480)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if self._icon_img:
            try:
                from PIL import ImageTk
                self._tk_icon = ImageTk.PhotoImage(
                    self._icon_img.resize((32, 32), Image.LANCZOS)
                )
                self.root.iconphoto(True, self._tk_icon)
            except Exception:
                pass

        self._build_header()
        self._build_controls()
        self._build_log_area()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=self.IG_PINK, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  📸  Instagram Analyzer",
                 font=("Segoe UI", 14, "bold"),
                 bg=self.IG_PINK, fg="white").pack(side="left", padx=14)
        tk.Label(hdr, text=APP_URL,
                 font=("Segoe UI", 9),
                 bg=self.IG_PINK, fg="#ffcdd2").pack(side="right", padx=14)

    def _build_controls(self):
        bar = tk.Frame(self.root, bg=self.BG2, pady=9)
        bar.pack(fill="x")

        # 상태 표시
        self._dot = tk.Label(bar, text="●", font=("Segoe UI", 15),
                              bg=self.BG2, fg=self.RED)
        self._dot.pack(side="left", padx=(14, 4))
        self._status_lbl = tk.Label(bar, text="서버 중지됨",
                                     font=("Segoe UI", 10, "bold"),
                                     bg=self.BG2, fg=self.FG)
        self._status_lbl.pack(side="left", padx=(0, 20))

        s = dict(font=("Segoe UI", 9, "bold"), relief="flat",
                 padx=14, pady=6, cursor="hand2", bd=0)

        self._btn_start = tk.Button(bar, text="▶  시작",
                                     bg=self.GREEN, fg="#0d1117",
                                     command=self._do_start, **s)
        self._btn_start.pack(side="left", padx=3)

        self._btn_stop = tk.Button(bar, text="■  중지",
                                    bg=self.RED, fg="white",
                                    command=self._do_stop, state="disabled", **s)
        self._btn_stop.pack(side="left", padx=3)

        self._btn_browser = tk.Button(bar, text="🌐  브라우저",
                                       bg="#1f6feb", fg="white",
                                       command=lambda: webbrowser.open(APP_URL),
                                       state="disabled", **s)
        self._btn_browser.pack(side="left", padx=3)

        if HAS_TRAY:
            tk.Button(bar, text="🔽  트레이로",
                      bg=self.BG3, fg=self.FG2,
                      command=self._hide_to_tray, **s).pack(side="right", padx=10)

    def _build_log_area(self):
        # 로그 헤더
        lhdr = tk.Frame(self.root, bg=self.BG, pady=5)
        lhdr.pack(fill="x", padx=12)

        tk.Label(lhdr, text="실시간 로그",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.BG, fg=self.FG2).pack(side="left")

        # 레벨 필터 라디오버튼
        self._level_var = tk.StringVar(value="ALL")
        for txt, col in [("ALL", self.FG2), ("INFO", self.BLUE),
                          ("WARNING", self.YELLOW), ("ERROR", self.RED)]:
            tk.Radiobutton(
                lhdr, text=txt, variable=self._level_var, value=txt,
                command=self._on_filter_change,
                bg=self.BG, fg=col, selectcolor=self.BG3,
                activebackground=self.BG, font=("Segoe UI", 8),
                relief="flat"
            ).pack(side="left", padx=5)

        # 자동 스크롤 + 지우기
        self._auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(lhdr, text="자동 스크롤",
                       variable=self._auto_var,
                       bg=self.BG, fg=self.FG2, selectcolor=self.BG3,
                       activebackground=self.BG,
                       font=("Segoe UI", 8)).pack(side="right")
        tk.Button(lhdr, text="지우기",
                  bg=self.BG, fg=self.FG2,
                  font=("Segoe UI", 8), relief="flat", bd=0,
                  command=self._clear_log).pack(side="right", padx=8)

        # 텍스트 + 스크롤바
        wrap = tk.Frame(self.root, bg=self.BG)
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._log = tk.Text(
            wrap,
            font=("Consolas", 8),
            bg="#010409", fg="#c9d1d9",
            relief="flat", bd=0,
            state="disabled",
            wrap="none",
            selectbackground="#264f78",
            insertbackground=self.FG,
        )
        sby = tk.Scrollbar(wrap, orient="vertical",
                           command=self._log.yview, bg=self.BG2)
        sbx = tk.Scrollbar(wrap, orient="horizontal",
                           command=self._log.xview, bg=self.BG2)
        self._log.configure(yscrollcommand=sby.set, xscrollcommand=sbx.set)
        sby.pack(side="right", fill="y")
        sbx.pack(side="bottom", fill="x")
        self._log.pack(fill="both", expand=True)

        for lvl, col in self.LEVEL_COLOR.items():
            self._log.tag_configure(lvl, foreground=col)
        self._log.tag_configure("TS",  foreground="#30363d")
        self._log.tag_configure("SEP", foreground="#30363d")

    # ── 트레이 ───────────────────────────────────────────────────────────────

    def _build_tray(self):
        if not (HAS_TRAY and self._icon_img):
            return
        menu = pystray.Menu(
            pystray.MenuItem("Instagram Analyzer 열기",
                             self._show_from_tray, default=True),
            pystray.MenuItem("브라우저에서 열기",
                             lambda i, it: webbrowser.open(APP_URL)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("서버 시작",
                             lambda i, it: self.root.after(0, self._do_start)),
            pystray.MenuItem("서버 중지",
                             lambda i, it: self.root.after(0, self._do_stop)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._quit_app),
        )
        self._tray = pystray.Icon(
            "instagram_analyzer", self._icon_img,
            "Instagram Analyzer", menu
        )
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _hide_to_tray(self):
        self.root.withdraw()

    def _show_from_tray(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)

    # ── 서버 제어 ─────────────────────────────────────────────────────────────

    def _do_start(self):
        if self.server.is_running():
            return
        started = self.server.start()
        if started:
            self._log_launcher("INFO", "서버 프로세스 시작됨")

    def _do_stop(self):
        self.server.stop()
        self._log_launcher("WARNING", "서버 프로세스 중지됨")

    def _log_launcher(self, level: str, msg: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [{level:<8}] launcher                 — {msg}"
        self._write_log_line(line, level)

    # ── 상태 폴링 ─────────────────────────────────────────────────────────────

    def _poll_status(self):
        alive = self.server.is_running()
        port_ok = self.server.is_port_open()
        if alive and port_ok:
            self._dot.config(fg=self.GREEN)
            self._status_lbl.config(text=f"서버 실행 중  ·  {APP_URL}")
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="normal")
            self._btn_browser.config(state="normal")
        elif alive and not port_ok:
            self._dot.config(fg=self.YELLOW)
            self._status_lbl.config(text="서버 시작 중…")
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="normal")
            self._btn_browser.config(state="disabled")
        else:
            self._dot.config(fg=self.RED)
            self._status_lbl.config(text="서버 중지됨")
            self._btn_start.config(state="normal")
            self._btn_stop.config(state="disabled")
            self._btn_browser.config(state="disabled")
        self.root.after(1500, self._poll_status)

    # ── 로그 파일 테일 ─────────────────────────────────────────────────────────

    def _seek_log_end(self):
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                    f.seek(0, 2)
                    self._log_pos = f.tell()
            except OSError:
                pass

    def _tail_log(self):
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                    f.seek(self._log_pos)
                    chunk = f.read()
                    self._log_pos = f.tell()
                if chunk:
                    lvl_filter = self._level_var.get()
                    for line in chunk.splitlines():
                        lvl = self._detect_level(line)
                        if self._passes_filter(lvl, lvl_filter):
                            self._write_log_line(line, lvl)
            except OSError:
                pass
        self.root.after(400, self._tail_log)

    @staticmethod
    def _detect_level(line: str) -> str:
        for lvl in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            if f"[{lvl}" in line:
                return lvl
        return "DEBUG"

    @staticmethod
    def _passes_filter(level: str, f: str) -> bool:
        order = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if f == "ALL":
            return True
        return order.index(level) >= order.index(f) if level in order and f in order else True

    def _write_log_line(self, line: str, level: str = "INFO"):
        self._log.config(state="normal")
        if len(line) > 19 and line[4] == "-" and line[10] == " ":
            self._log.insert("end", line[:19], "TS")
            self._log.insert("end", line[19:] + "\n", level)
        else:
            self._log.insert("end", line + "\n", level)
        # 최대 3000줄
        if int(self._log.index("end-1c").split(".")[0]) > 3000:
            self._log.delete("1.0", "600.0")
        self._log.config(state="disabled")
        if self._auto_var.get():
            self._log.see("end")

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _on_filter_change(self):
        self._clear_log()
        self._log_pos = 0
        if LOG_FILE.exists():
            try:
                lvl_filter = self._level_var.get()
                with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    self._log_pos = f.tell()
                for line in lines[-500:]:
                    line = line.rstrip()
                    lvl = self._detect_level(line)
                    if self._passes_filter(lvl, lvl_filter):
                        self._write_log_line(line, lvl)
            except OSError:
                pass

    # ── 종료 ──────────────────────────────────────────────────────────────────

    def _on_close(self):
        if self.server.is_running():
            ans = messagebox.askyesnocancel(
                "Instagram Analyzer",
                "서버가 실행 중입니다.\n\n"
                "예 → 서버 중지 후 종료\n아니오 → 트레이로 최소화",
                icon="question"
            )
            if ans is True:
                self._quit_app()
            elif ans is False and HAS_TRAY and self._tray:
                self._hide_to_tray()
        else:
            self._quit_app()

    def _quit_app(self, icon=None, item=None):
        self.server.stop()
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not HAS_TRAY:
        print("트레이 아이콘을 사용하려면: pip install pystray Pillow")
    try:
        from PIL import Image  # noqa: F401 (명시적 임포트 확인)
    except ImportError:
        pass
    LauncherApp().run()
