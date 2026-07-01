"""
사그라다 파밀리아 티켓 봇 — GUI 런처
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python"
MAIN_PY = PROJECT_DIR / "main.py"
ENV_PATH = PROJECT_DIR / ".env"


def _load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _save_env(updates: dict):
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    written = set()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                result.append(f"{k}={updates[k]}")
                written.add(k)
            else:
                result.append(line)
        else:
            result.append(line)
    for k, v in updates.items():
        if k not in written:
            result.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(result) + "\n", encoding="utf-8")


class _ColorBtn(tk.Frame):
    """macOS tkinter은 tk.Button bg가 무시되므로 Frame+Label로 구현."""
    def __init__(self, parent, text, command, bg, fg="white", font=("", 14, "bold"), **kw):
        super().__init__(parent, bg=bg, cursor="hand2")
        self._bg_on  = bg
        self._bg_dis = "#aaaaaa"
        self._fg_on  = fg
        self._cmd    = command
        self._enabled = True
        self._lbl = tk.Label(self, text=text, bg=bg, fg=fg, font=font,
                             padx=16, pady=10, cursor="hand2")
        self._lbl.pack(fill="both", expand=True)
        for w in (self, self._lbl):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    self._enter)
            w.bind("<Leave>",    self._leave)

    def _click(self, _=None):
        if self._enabled:
            self._cmd()

    def _enter(self, _=None):
        if self._enabled:
            darker = self._darken(self._bg_on)
            self.configure(bg=darker)
            self._lbl.configure(bg=darker)

    def _leave(self, _=None):
        if self._enabled:
            self.configure(bg=self._bg_on)
            self._lbl.configure(bg=self._bg_on)

    @staticmethod
    def _darken(h):
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return f"#{int(r*.78):02x}{int(g*.78):02x}{int(b*.78):02x}"

    def configure(self, **kw):
        if "state" in kw:
            self._enabled = (kw.pop("state") != "disabled")
            col = self._bg_on if self._enabled else self._bg_dis
            fg  = self._fg_on if self._enabled else "#666666"
            super().configure(bg=col)
            self._lbl.configure(bg=col, fg=fg)
        if kw:
            super().configure(**kw)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("사그라다 파밀리아 티켓 봇")
        self.resizable(False, False)
        self._proc = None
        self._build()
        self._load()

    # ── UI 구성 ─────────────────────────────────────────────

    def _entry_row(self, parent, label, row, hint=""):
        tk.Label(parent, text=label, anchor="w", width=18).grid(
            row=row, column=0, sticky="w", padx=(10, 4), pady=5)
        var = tk.StringVar()
        ent = tk.Entry(parent, textvariable=var, width=36)
        ent.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=5)
        if hint:
            tk.Label(parent, text=hint, fg="#888", font=("", 10)).grid(
                row=row + 1, column=1, sticky="w", padx=(0, 10))
        return var

    def _build(self):
        P = {"padx": 14, "pady": 6, "fill": "x"}

        # ── 예매 설정 ──
        f1 = ttk.LabelFrame(self, text="  예매 설정  ")
        f1.pack(**P)
        f1.columnconfigure(1, weight=1)
        self.v_date = self._entry_row(f1, "날짜", 0, "예: 2026-07-30,2026-07-31  (쉼표로 다중 입력)")
        self.v_time = self._entry_row(f1, "시간", 2, "예: 10:00,10:15,13:00  (쉼표로 다중 입력, 15분 간격)")

        tk.Label(f1, text="인원 수", anchor="w", width=18).grid(
            row=4, column=0, sticky="w", padx=(10, 4), pady=5)
        self.v_people = tk.StringVar(value="2")
        tk.Spinbox(f1, from_=1, to=10, textvariable=self.v_people, width=6,
                   font=("", 13)).grid(row=4, column=1, sticky="w", padx=(0, 10), pady=5)

        tk.Label(f1, text="동시 진행 수", anchor="w", width=18).grid(
            row=5, column=0, sticky="w", padx=(10, 4), pady=5)
        self.v_parallel = tk.StringVar(value="1")
        tk.Spinbox(f1, from_=1, to=4, textvariable=self.v_parallel, width=6,
                   font=("", 13)).grid(row=5, column=1, sticky="w", padx=(0, 10), pady=5)
        tk.Label(f1, text="날짜를 N개 그룹으로 나눠 동시 진행", fg="#888", font=("", 10)).grid(
            row=6, column=1, sticky="w", padx=(0, 10))

        self.v_keep_browser = tk.BooleanVar()
        tk.Checkbutton(
            f1, text="브라우저 유지 모드  (크롬을 한 번만 열고 최소화 유지 — 체크아웃 시에만 화면 표시)",
            variable=self.v_keep_browser, anchor="w",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=(6, 10), pady=(2, 6))

        # ── 방문자 1 ──
        f2 = ttk.LabelFrame(self, text="  방문자 1  ")
        f2.pack(**P)
        f2.columnconfigure(1, weight=1)
        self.v_p1_name = self._entry_row(f2, "이름 (영문)", 0)
        self.v_p1_sur  = self._entry_row(f2, "성 (영문)", 1)
        self.v_p1_pp   = self._entry_row(f2, "여권번호", 2)

        # ── 방문자 2 ──
        f3 = ttk.LabelFrame(self, text="  방문자 2  ")
        f3.pack(**P)
        f3.columnconfigure(1, weight=1)
        self.v_p2_name = self._entry_row(f3, "이름 (영문)", 0)
        self.v_p2_sur  = self._entry_row(f3, "성 (영문)", 1)
        self.v_p2_pp   = self._entry_row(f3, "여권번호", 2)

        # ── 버튼 ──
        bf = tk.Frame(self)
        bf.pack(fill="x", padx=14, pady=8)
        self.btn_start = _ColorBtn(bf, "▶  모니터링 시작", self._start, bg="#00b341")
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop = _ColorBtn(bf, "■  중지", self._stop, bg="#e03030")
        self.btn_stop.configure(state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True)

        # ── 로그 ──
        lf = ttk.LabelFrame(self, text="  로그  ")
        lf.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log = scrolledtext.ScrolledText(
            lf, state="disabled", height=15, font=("Courier", 11),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.log.pack(fill="both", expand=True, padx=6, pady=6)

        # 클릭 시 포커스 이동 + Ctrl/Cmd+A, Ctrl/Cmd+C 직접 바인딩
        self.log.bind("<Button-1>", lambda e: self.log.focus_set())
        for seq in ("<Control-a>", "<Command-a>"):
            self.log.bind(seq, self._log_select_all)
        for seq in ("<Control-c>", "<Command-c>"):
            self.log.bind(seq, self._log_copy)

    # ── 데이터 ───────────────────────────────────────────────

    def _load(self):
        e = _load_env()
        self.v_date.set(e.get("TARGET_DATE", ""))
        self.v_time.set(e.get("TARGET_TIME", ""))
        self.v_people.set(e.get("NUM_PEOPLE", "2"))
        self.v_parallel.set(e.get("PARALLEL_COUNT", "1"))
        self.v_keep_browser.set(e.get("KEEP_BROWSER", "false").lower() == "true")
        self.v_p1_name.set(e.get("PERSON1_NAME", ""))
        self.v_p1_sur.set(e.get("PERSON1_SURNAME", ""))
        self.v_p1_pp.set(e.get("PERSON1_PASSPORT", ""))
        self.v_p2_name.set(e.get("PERSON2_NAME", ""))
        self.v_p2_sur.set(e.get("PERSON2_SURNAME", ""))
        self.v_p2_pp.set(e.get("PERSON2_PASSPORT", ""))

    def _save(self):
        _save_env({
            "TARGET_DATE":      self.v_date.get().strip(),
            "TARGET_TIME":      self.v_time.get().strip(),
            "NUM_PEOPLE":       self.v_people.get().strip(),
            "PARALLEL_COUNT":   self.v_parallel.get().strip(),
            "KEEP_BROWSER":     "true" if self.v_keep_browser.get() else "false",
            "PERSON1_NAME":     self.v_p1_name.get().strip(),
            "PERSON1_SURNAME":  self.v_p1_sur.get().strip(),
            "PERSON1_PASSPORT": self.v_p1_pp.get().strip(),
            "PERSON2_NAME":     self.v_p2_name.get().strip(),
            "PERSON2_SURNAME":  self.v_p2_sur.get().strip(),
            "PERSON2_PASSPORT": self.v_p2_pp.get().strip(),
        })

    # ── 실행 ────────────────────────────────────────────────

    def _validate(self) -> bool:
        if not self.v_date.get().strip():
            messagebox.showwarning("입력 오류", "날짜를 입력해주세요.")
            return False
        if not self.v_time.get().strip():
            messagebox.showwarning("입력 오류", "시간을 입력해주세요.")
            return False
        if not self.v_p1_name.get().strip() or not self.v_p1_sur.get().strip():
            messagebox.showwarning("입력 오류", "방문자 1의 이름과 성을 입력해주세요.")
            return False
        return True

    def _start(self):
        if not self._validate():
            return
        self._save()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._append("=== 모니터링 시작 ===\n")

        self._proc = subprocess.Popen(
            [str(VENV_PYTHON), str(MAIN_PY), "--auto-book"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            cwd=str(PROJECT_DIR),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        threading.Thread(target=self._stream, daemon=True).start()

    def _stream(self):
        for line in self._proc.stdout:
            self.after(0, self._append, line)
        self.after(0, self._done)

    def _done(self):
        self._proc = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self._append("=== 종료됨 ===\n")

    def _stop(self):
        if self._proc:
            self._proc.terminate()

    def _log_select_all(self, event=None):
        self.log.tag_add("sel", "1.0", "end")
        return "break"

    def _log_copy(self, event=None):
        try:
            text = self.log.get("sel.first", "sel.last")
        except tk.TclError:
            text = self.log.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        return "break"

    def _append(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def on_close(self):
        if self._proc:
            self._proc.terminate()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
