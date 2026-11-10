"""Unsupervised Adults SMP Windows launcher with an official portable Prism backend.

Our UI updates the pinned modpack, keeps all data beside the EXE and asks Prism
only to manage accounts, Minecraft, Fabric, Java and the game process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import ua_core as core
import ua_prism as prism
import ua_server

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
            messagebox.showerror(
                "Unsupervised Adults MC - Storage",
                "The EXE's folder isn't writable. Move it to D:\\Games\\UnsupervisedAdultsMC "
                "or another writable folder.\n\n" + str(exc),
            )
            error_window.destroy()
            raise SystemExit(1) from exc
        self.settings = self._load_settings()
        self.events = queue.Queue()
        self.busy = False
        self.window = tk.Tk()
        self.window.title("Unsupervised Adults MC")
        self.window.geometry("900x625")
        self.window.minsize(760, 575)
        self.window.configure(bg=BG)
        self._make_ui()
        self.window.after(100, self._pump)
        self.log("Minecraft 1.21.1  /  Fabric  /  Auto-updating SMP")
        self.log("Prism manages your Minecraft account, Java and game files. Our launcher manages the modpack.")
        if prism.has_prism_account_file(self.app_dir):
            self.account_var.set("PRISM ACCOUNT FILE FOUND (SESSION VERIFIED BY PRISM)")
        else:
            self.log("First run: click PLAY. Prism opens for a one-time Microsoft sign-in.")

    def _load_settings(self) -> dict:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_settings(self, *_):
        try:
            address = prism.validate_server_address(self.server_var.get())
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
        tk.Label(heading, text="U / A", fg=BLUE, bg=BG,
                 font=("Segoe UI Black", 23, "bold")).pack(side=tk.LEFT, padx=(0, 22))
        title_col = tk.Frame(heading, bg=BG)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_col, text="UNSUPERVISED ADULTS", fg=TEXT, bg=BG,
                 font=("Segoe UI Semibold", 22, "bold"), anchor="w").pack(anchor="w")
        tk.Label(title_col, text="MINECRAFT SMP   /   MODDED SURVIVAL", fg=MUTED, bg=BG,
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w", pady=(1, 0))

        hero = tk.Frame(root, bg=PANEL, padx=28, pady=22,
                        highlightbackground="#43345e", highlightthickness=1)
        hero.pack(fill=tk.X, pady=(22, 16))
        tk.Label(hero, text="YOUR WORLD. ONE CLICK AWAY.", fg=TEXT, bg=PANEL,
                 font=("Segoe UI Semibold", 17, "bold")).pack(anchor="w")
        tk.Label(hero, text="Minecraft 1.21.1 • Fabric • Modpack updates handled automatically",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 10)).pack(anchor="w", pady=(5, 16))
        self.play = tk.Button(hero, text="▶  PLAY SMP", command=self.play_click,
                              bg=PURPLE, fg="#140c22", activebackground="#b792f0",
                              activeforeground="#140c22", relief=tk.FLAT, borderwidth=0,
                              cursor="hand2", font=("Segoe UI", 15, "bold"), pady=12)
        self.play.pack(fill=tk.X)
        tk.Label(hero, text="First time? Prism will open once to set up your Microsoft account.",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

        server = tk.Frame(root, bg=BG)
        server.pack(fill=tk.X)
        tk.Label(server, text="SMP SERVER", fg=BLUE, bg=BG,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.server_var = tk.StringVar(value=self.settings.get("server_address", ""))
        self.server_entry = tk.Entry(server, textvariable=self.server_var, bg=PANEL_ALT,
                                     fg=TEXT, insertbackground=TEXT, relief=tk.FLAT,
                                     font=("Segoe UI", 11), bd=10)
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 10))
        self.server_entry.bind("<Return>", self._save_settings)
        self.save_btn = tk.Button(server, text="SAVE", command=self._save_settings,
                                  bg=PANEL_ALT, fg=TEXT, relief=tk.FLAT,
                                  activebackground="#4a385e", cursor="hand2",
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        self.save_btn.pack(side=tk.RIGHT)

        self.account_var = tk.StringVar(value="MICROSOFT ACCOUNT: SET UP IN PRISM")
        tk.Label(root, textvariable=self.account_var, fg=BLUE, bg=BG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(14, 0))
        buttons = tk.Frame(root, bg=BG)
        buttons.pack(fill=tk.X, pady=(12, 12))
        options = [
            ("ACCOUNT / SETTINGS", self.login_click),
            ("CHECK / UPDATE MODS", self.update_click),
            ("OPEN GAME FOLDER", self.folder_click),
            ("CREATE SERVER ZIP", self.create_server_click),
        ]
        self.small_buttons = []
        for label, action in options:
            button = tk.Button(buttons, text=label, command=action, bg=PANEL_ALT, fg=TEXT,
                               activebackground="#4a385e", activeforeground=TEXT,
                               relief=tk.FLAT, font=("Segoe UI", 9, "bold"),
                               cursor="hand2", pady=11, padx=8)
            button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            self.small_buttons.append(button)

        self.status_var = tk.StringVar(value="READY")
        tk.Label(root, textvariable=self.status_var, fg=BLUE, bg=BG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 5))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("UA.Horizontal.TProgressbar", background=PURPLE,
                        troughcolor=PANEL_ALT, bordercolor=PANEL_ALT,
                        lightcolor=PURPLE, darkcolor=PURPLE)
        self.bar = ttk.Progressbar(root, mode="determinate", maximum=100,
                                   style="UA.Horizontal.TProgressbar")
        self.bar.pack(fill=tk.X, pady=(0, 10))
        self.console = tk.Text(root, bg="#120e19", fg="#cfc4dd", relief=tk.FLAT,
                               state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9),
                               height=8, bd=12, selectbackground="#5c437f")
        self.console.pack(fill=tk.BOTH, expand=True)
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X, pady=(12, 0))
        tk.Label(footer, text="Portable • Microsoft sign-in through Prism • No Crafty access needed",
                 fg=MUTED, bg=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        link = tk.Label(footer, text="PROJECT ON GITHUB", fg=BLUE, bg=BG,
                        cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(side=tk.RIGHT)
        link.bind("<Button-1>", lambda _: webbrowser.open(
            "https://github.com/TechX1320/UnsupervisedAdultsMC"))

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
                elif kind == "notice":
                    messagebox.showinfo("Unsupervised Adults MC", value)
                elif kind == "error":
                    self.status_var.set("ACTION FAILED — SEE MESSAGE")
                    self.log("ERROR: " + value)
                    messagebox.showerror("Unsupervised Adults MC", value)
                elif kind == "complete":
                    self.busy = False
                    for button in [self.play, *self.small_buttons]:
                        button.configure(state=tk.NORMAL)
                    if value is not None:
                        self.status_var.set(value)
                    self.account_var.set("PRISM ACCOUNT FILE FOUND (SESSION VERIFIED BY PRISM)"
                                         if prism.has_prism_account_file(self.app_dir)
                                         else "MICROSOFT ACCOUNT: SET UP IN PRISM")
        except queue.Empty:
            pass
        self.window.after(100, self._pump)

    def _run(self, task):
        if self.busy:
            return
        self.busy = True
        self.bar["value"] = 0
        for button in [self.play, *self.small_buttons]:
            button.configure(state=tk.DISABLED)
        def worker():
            result = None
            try:
                result = task() or "READY"
            except Exception as exc:
                self._emit("error", f"{type(exc).__name__}: {exc}")
            finally:
                self._emit("complete", result)
        threading.Thread(target=worker, daemon=True).start()

    def login_click(self):
        def task():
            status = lambda s: self._emit("log", s)
            exe = prism.ensure_prism(self.app_dir, status)
            catalog = core.get_remote_catalog(status)
            prism.ensure_instance(self.app_dir, catalog, status)
            status("Opening Prism: Accounts > Add Microsoft account. Close Prism when done.")
            prism.open_prism(self.app_dir, exe)
            return "ACCOUNT SETUP OPENED IN PRISM"
        self._run(task)

    def update_click(self):
        self._run(lambda: self._sync(launch=False))

    def play_click(self):
        if self._save_settings():
            self._run(lambda: self._sync(launch=True))

    def _sync(self, launch: bool) -> str:
        status = lambda s: self._emit("log", s)
        catalog = core.get_remote_catalog(status)
        exe = prism.ensure_prism(self.app_dir, status)
        self._emit("progress", 0.08)
        lock = core.load_lock(catalog, self.app_dir, status)
        missing_required = core.unresolved_required(lock)
        if missing_required:
            raise RuntimeError("Required mods unavailable: " + ", ".join(missing_required) +
                               ". The pack owner must fix the catalog/lock.")
        instance = prism.ensure_instance(self.app_dir, catalog, status)
        prism.migrate_legacy(self.app_dir, instance, status)
        result = core.install_client(lock, instance, status,
                                     lambda value: self._emit("progress", .08 + value * .9))
        missing = core.manual_warnings(lock) + result["failed"]
        status(f"Modpack: {result['count']} files checked, {result['updated']} updated, "
               f"{len(missing)} manual/unavailable.")
        if missing:
            report = [f"{x['name']}: {x.get('reason', '')}\n{x.get('page', '')}" for x in missing]
            (instance / "ua-missing-mods.txt").write_text("\n\n".join(report) + "\n", encoding="utf-8")
            status("Optional missing mods are listed in the game folder (ua-missing-mods.txt).")
        else:
            (instance / "ua-missing-mods.txt").unlink(missing_ok=True)
        self._emit("progress", 1.0)
        if not launch:
            status("Prism and our modpack are ready. Minecraft and Java are verified when you click Play.")
            return "MODPACK CHECKED"
        if not prism.has_prism_account_file(self.app_dir):
            status("First launch: opening Prism to add your Microsoft account. Return and click Play when signed in.")
            prism.open_prism(self.app_dir, exe)
            self._emit("notice", "First-time setup: Prism Launcher has opened.\n\n"
                       "1. Follow the Prism setup wizard.\n"
                       "2. Go to Accounts and add your Microsoft Minecraft account.\n"
                       "3. Return here and click PLAY SMP again.\n\n"
                       "Your modpack is already installed, and your account stays in Prism.")
            return "SIGN IN IN PRISM, THEN CLICK PLAY"
        server = prism.validate_server_address(
            self.settings.get("server_address") or catalog.get("server_address", ""))
        if not server:
            status("No SMP server address configured. Minecraft will open its main menu.")
        status("Starting our SMP instance through Prism. Prism handles Minecraft, Java and Fabric.")
        prism.launch_instance(self.app_dir, exe, server)
        return "MINECRAFT LAUNCH REQUESTED"

    def create_server_click(self):
        """Owner-only convenience button; it never contacts Crafty directly."""
        self._run(self._create_server_zip)

    def _create_server_zip(self) -> str:
        status = lambda message: self._emit("log", message)
        catalog = core.get_remote_catalog(status)
        lock = core.load_lock(catalog, self.app_dir, status)
        archive = ua_server.build_server_zip(
            self.app_dir, catalog, lock, status=status,
            progress=lambda fraction: self._emit("progress", fraction),
        )
        self._emit("notice", "Crafty server ZIP created!\n\n"
                   + str(archive) + "\n\n"
                   "In Crafty: Create New Server > Upload Zip Archive. "
                   "Choose the ZIP root and fabric-server-launch.jar as the executable. "
                   "Use Java 21. Read CRAFTY-IMPORT.txt before starting.")
        if os.name == "nt":
            try:
                os.startfile(str(archive.parent))
            except OSError as exc:
                status("Could not open the ZIP folder automatically: " + str(exc))
        return "CRAFTY SERVER ZIP READY"

    def folder_click(self):
        folder = prism.data_dir(self.app_dir) / "instances" / core.PACK_ID / ".minecraft"
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            self.log("Game folder: " + str(folder))

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    Launcher().run()
