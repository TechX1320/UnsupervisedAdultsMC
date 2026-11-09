"""Unsupervised Adults MC: an all-in-one Windows Minecraft/Fabric/modpack launcher.

The EXE built with PyInstaller is the only launcher program players install.
Official Microsoft sign-in runs in the system browser and returns to this app.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import ua_auth as auth
import ua_core as core
import ua_minecraft as minecraft

BG = "#16121f"
PANEL = "#211a31"
PANEL_ALT = "#2b223d"
TEXT = "#f6f3ff"
MUTED = "#b2a8c8"
PURPLE = "#9e65ee"
BLUE = "#8cdafa"


class Launcher:
    def __init__(self):
        self.app_dir = core.app_root()
        self.settings_path = self.app_dir / "settings.json"
        try:
            self.app_dir.mkdir(parents=True, exist_ok=True)
            testfile = self.app_dir / ".ua-write-test"
            testfile.write_bytes(b"ok")
            testfile.unlink()
        except OSError as exc:
            error_window = tk.Tk()
            error_window.withdraw()
            messagebox.showerror("Unsupervised Adults MC - Storage", 
                "The launcher's folder is not writable. Move the EXE to a folder such as "
                "D:\\Games\\UnsupervisedAdultsMC and run it there.\n\n" + str(exc))
            error_window.destroy()
            raise SystemExit(1) from exc
        self.settings = self._load_settings()
        self.events = queue.Queue()
        self.busy = False
        self._session = None
        self._session_at = 0.0
        self._device_dialog = None
        self.window = tk.Tk()
        self.window.title("Unsupervised Adults MC")
        self.window.geometry("900x625")
        self.window.minsize(760, 575)
        self.window.configure(bg=BG)
        self._make_ui()
        self.window.after(100, self._pump)
        self.log("Minecraft 1.21.1  /  Fabric  /  Auto-updating SMP")
        self.log("One launcher, one click. No Prism or other Minecraft launcher required.")
        try:
            account = auth.load_account(self.app_dir)
            if account:
                self.account_var.set("SIGNED IN: " + account["name"])
                self.log("Welcome back, " + account["name"] + ".")
        except auth.AuthenticationError as exc:
            self.log(str(exc))

    def _load_settings(self):
        try:
            s = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return s if isinstance(s, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_settings(self, *_):
        address = self.server_var.get().strip()
        try:
            minecraft.server_options(address)
        except ValueError as exc:
            messagebox.showerror("Invalid server", str(exc))
            return False
        self.settings["server_address"] = address
        self.settings_path.write_text(json.dumps(self.settings, indent=2) + "\n", encoding="utf-8")
        return True

    def _make_ui(self):
        root = tk.Frame(self.window, bg=BG)
        root.pack(fill=tk.BOTH, expand=True, padx=34, pady=28)
        heading = tk.Frame(root, bg=BG)
        heading.pack(fill=tk.X)
        tk.Label(heading, text="U / A", fg=BLUE, bg=BG, font=("Segoe UI Black", 23, "bold")).pack(side=tk.LEFT, padx=(0, 22))
        title_col = tk.Frame(heading, bg=BG)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_col, text="UNSUPERVISED ADULTS", fg=TEXT, bg=BG,
                 font=("Segoe UI Semibold", 22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(title_col, text="MINECRAFT SMP   /   MODDED SURVIVAL", fg=MUTED, bg=BG,
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w", pady=(1, 0))

        hero = tk.Frame(root, bg=PANEL, padx=28, pady=22, highlightbackground="#43345e", highlightthickness=1)
        hero.pack(fill=tk.X, pady=(22, 16))
        tk.Label(hero, text="YOUR WORLD. ONE CLICK AWAY.", fg=TEXT, bg=PANEL,
                 font=("Segoe UI Semibold", 17, "bold")).pack(anchor="w")
        tk.Label(hero, text="Installs Minecraft + Java + Fabric + mods automatically", fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(5, 16))
        self.play = tk.Button(hero, text="▶  PLAY SMP", command=self.play_click, bg=PURPLE, fg="#140c22",
                              activebackground="#b792f0", activeforeground="#140c22", relief=tk.FLAT,
                              borderwidth=0, cursor="hand2", font=("Segoe UI", 15, "bold"), pady=12)
        self.play.pack(fill=tk.X)
        tk.Label(hero, text="First run: sign in with Microsoft in your browser. Then the launcher takes over.",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

        server = tk.Frame(root, bg=BG)
        server.pack(fill=tk.X)
        tk.Label(server, text="SMP SERVER", fg=BLUE, bg=BG, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.server_var = tk.StringVar(value=self.settings.get("server_address", ""))
        self.server_entry = tk.Entry(server, textvariable=self.server_var, bg=PANEL_ALT, fg=TEXT,
                                     insertbackground=TEXT, relief=tk.FLAT, font=("Segoe UI", 11), bd=10)
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 10))
        self.server_entry.bind("<Return>", self._save_settings)
        self.save_btn = tk.Button(server, text="SAVE", command=self._save_settings, bg=PANEL_ALT,
                                  fg=TEXT, relief=tk.FLAT, activebackground="#4a385e", cursor="hand2",
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        self.save_btn.pack(side=tk.RIGHT)

        self.account_var = tk.StringVar(value="MICROSOFT ACCOUNT: NOT SIGNED IN")
        tk.Label(root, textvariable=self.account_var, fg=BLUE, bg=BG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(14, 0))

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(fill=tk.X, pady=(12, 12))
        options = [
            ("SIGN IN WITH MICROSOFT", self.login_click),
            ("CHECK / REPAIR", self.update_click),
            ("OPEN GAME FOLDER", self.folder_click),
        ]
        self.small_buttons = []
        for label, action in options:
            button = tk.Button(buttons, text=label, command=action, bg=PANEL_ALT, fg=TEXT,
                               activebackground="#4a385e", activeforeground=TEXT, relief=tk.FLAT,
                               font=("Segoe UI", 9, "bold"), cursor="hand2", pady=11, padx=8)
            button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            self.small_buttons.append(button)

        self.status_var = tk.StringVar(value="READY")
        tk.Label(root, textvariable=self.status_var, fg=BLUE, bg=BG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 5))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("UA.Horizontal.TProgressbar", background=PURPLE, troughcolor=PANEL_ALT,
                        bordercolor=PANEL_ALT, lightcolor=PURPLE, darkcolor=PURPLE)
        self.bar = ttk.Progressbar(root, mode="determinate", maximum=100, style="UA.Horizontal.TProgressbar")
        self.bar.pack(fill=tk.X, pady=(0, 10))
        self.console = tk.Text(root, bg="#120e19", fg="#cfc4dd", relief=tk.FLAT, state=tk.DISABLED,
                               wrap=tk.WORD, font=("Consolas", 9), height=8, bd=12, selectbackground="#5c437f")
        self.console.pack(fill=tk.BOTH, expand=True)
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X, pady=(12, 0))
        tk.Label(footer, text="Microsoft sign-in  •  Dedicated Fabric instance  •  Online-mode SMP",
                 fg=MUTED, bg=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        link = tk.Label(footer, text="PROJECT ON GITHUB", fg=BLUE, bg=BG, cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side=tk.RIGHT)
        link.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/TechX1320/UnsupervisedAdultsMC"))

    def log(self, message: str):
        self.console.configure(state=tk.NORMAL)
        self.console.insert(tk.END, str(message) + "\n")
        self.console.see(tk.END)
        self.console.configure(state=tk.DISABLED)

    def _emit(self, kind: str, value=None):
        self.events.put((kind, value))

    def _pump(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log(value)
                    self.status_var.set(str(value)[:90])
                elif kind == "progress":
                    self.bar["value"] = min(100, max(0, value * 100))
                elif kind == "account":
                    self._close_device_dialog()
                    self.account_var.set("SIGNED IN: " + value)
                elif kind == "device":
                    self._show_device_dialog(*value)
                elif kind == "close_device":
                    self._close_device_dialog()
                elif kind == "error":
                    self._close_device_dialog()
                    self.status_var.set("ACTION FAILED — SEE MESSAGE")
                    self.log("ERROR: " + value)
                    messagebox.showerror("Unsupervised Adults MC", value)
                elif kind == "complete":
                    self.busy = False
                    for button in [self.play, *self.small_buttons]:
                        button.configure(state=tk.NORMAL)
                    if value:
                        self.status_var.set("READY")
        except queue.Empty:
            pass
        self.window.after(100, self._pump)

    def _close_device_dialog(self):
        if self._device_dialog is not None:
            try:
                self._device_dialog.destroy()
            except tk.TclError:
                pass
            self._device_dialog = None

    def _show_device_dialog(self, url: str, code: str):
        self._close_device_dialog()
        dialog = tk.Toplevel(self.window)
        self._device_dialog = dialog
        dialog.title("Sign in with Microsoft")
        dialog.geometry("480x290")
        dialog.resizable(False, False)
        dialog.configure(bg=PANEL)
        dialog.transient(self.window)
        dialog.grab_set()
        tk.Label(dialog, text="MICROSOFT SIGN-IN", fg=TEXT, bg=PANEL,
                 font=("Segoe UI", 17, "bold")).pack(pady=(23, 7))
        tk.Label(dialog, text="Open the link, sign in, then enter this code:",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 10)).pack()
        code_entry = tk.Entry(dialog, justify="center", font=("Consolas", 20, "bold"),
                              fg=BLUE, bg=PANEL_ALT, relief=tk.FLAT, width=18)
        code_entry.insert(0, code)
        code_entry.configure(state="readonly")
        code_entry.pack(pady=15)
        def copy_code():
            dialog.clipboard_clear()
            dialog.clipboard_append(code)
            dialog.update_idletasks()
        buttons = tk.Frame(dialog, bg=PANEL)
        buttons.pack()
        tk.Button(buttons, text="OPEN MICROSOFT", command=lambda: webbrowser.open(url),
                  bg=PURPLE, fg="#140c22", relief=tk.FLAT, padx=14, pady=9).pack(side=tk.LEFT, padx=7)
        tk.Button(buttons, text="COPY CODE", command=copy_code,
                  bg=PANEL_ALT, fg=TEXT, relief=tk.FLAT, padx=14, pady=9).pack(side=tk.LEFT, padx=7)
        tk.Label(dialog, text=url, fg=BLUE, bg=PANEL,
                 font=("Segoe UI", 9)).pack(pady=(16, 5))
        tk.Label(dialog, text="Leave this window open while you sign in.",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 9)).pack()
        webbrowser.open(url)

    def _run(self, task):
        if self.busy:
            return
        self.busy = True
        self.bar["value"] = 0
        for button in [self.play, *self.small_buttons]:
            button.configure(state=tk.DISABLED)
        def worker():
            success = False
            try:
                task()
                success = True
            except Exception as exc:
                self._emit("error", f"{type(exc).__name__}: {exc}")
            finally:
                self._emit("complete", success)
        threading.Thread(target=worker, daemon=True).start()

    def _login(self, catalog: dict) -> dict:
        client_id = auth.require_client_id(catalog)
        try:
            session = auth.microsoft_device_login(
                client_id, lambda s: self._emit("log", s),
                lambda url, code: self._emit("device", (url, code)))
        except auth.DeviceCodeUnavailable:
            self._emit("close_device")
            self._emit("log", "Microsoft requires browser sign-in for this app. Opening browser...")
            session = auth.microsoft_login(client_id, lambda s: self._emit("log", s))
        auth.save_account(self.app_dir, session)
        self._session = session
        self._session_at = time.monotonic()
        self._emit("account", session["name"])
        self._emit("log", "Signed in as " + session["name"] + ".")
        return session

    def _get_session(self, catalog: dict) -> dict:
        client_id = auth.require_client_id(catalog)
        if self._session and time.monotonic() - self._session_at < 45 * 60:
            return self._session
        saved = auth.load_account(self.app_dir)
        if saved:
            self._emit("log", "Refreshing Microsoft session...")
            try:
                session = auth.refresh_account(self.app_dir, client_id)
            except auth.AuthenticationError:
                session = self._login(catalog)
            else:
                self._session = session
                self._session_at = time.monotonic()
                self._emit("account", session["name"])
            return session
        return self._login(catalog)

    def login_click(self):
        self._run(lambda: self._login(core.get_remote_catalog(lambda s: self._emit("log", s))))

    def update_click(self):
        self._run(lambda: self._sync(launch=False))

    def play_click(self):
        if self._save_settings():
            self._run(lambda: self._sync(launch=True))

    def _sync(self, launch: bool):
        status = lambda s: self._emit("log", s)
        catalog = core.get_remote_catalog(status)
        session = self._get_session(catalog) if launch else None
        lock = core.load_lock(catalog, self.app_dir, status)
        if core.unresolved_required(lock):
            raise RuntimeError("Required mods unavailable: " + ", ".join(core.unresolved_required(lock)))
        instance = core.ensure_instance(self.app_dir, catalog)
        game = instance / ".minecraft"
        result = core.install_client(lock, instance, status, lambda value: self._emit("progress", value * .35))
        missing = core.manual_warnings(lock) + result["failed"]
        status(f"Modpack: {result['count']} files checked, {result['updated']} downloaded, {len(missing)} unavailable.")
        if missing:
            report = [f"{x['name']}: {x.get('reason', '')}\n{x.get('page', '')}" for x in missing]
            (instance / "ua-missing-mods.txt").write_text("\n\n".join(report) + "\n", encoding="utf-8")
            status("Some optional mods require owner attention. See ua-missing-mods.txt in the game folder.")
        minecraft.ensure_game(game, catalog, status, lambda value: self._emit("progress", .35 + value * .65))
        if launch:
            server = self.settings.get("server_address") or catalog.get("server_address", "")
            if not server:
                status("No SMP server address set. Minecraft will open its main menu.")
            status("Starting Minecraft directly from Unsupervised Adults MC...")
            minecraft.start_game(game, catalog, session, server, self.app_dir / "logs")
            status("Minecraft started. Have fun!")
        else:
            status("Minecraft, Fabric, Java and the modpack are installed and repaired.")
        self._emit("progress", 1.0)

    def folder_click(self):
        folder = self.app_dir / "instance" / ".minecraft"
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            self.log("Game folder: " + str(folder))

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    Launcher().run()
