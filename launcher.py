"""Unsupervised Adults SMP launcher for Windows.

Prism Launcher, installed from its official verified release, performs
Microsoft/Minecraft login. This application never sees account credentials.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import ua_core as core

# Palette: purple / black / white / pale blue. No extra services needed.
BG = "#16121f"
PANEL = "#211a31"
PANEL_ALT = "#2b223d"
TEXT = "#f6f3ff"
MUTED = "#b2a8c8"
PURPLE = "#9e65ee"
BLUE = "#8cdafa"
ERROR = "#ff9ba3"


class Launcher:
    def __init__(self):
        self.app_dir = core.app_root()
        self.settings_path = self.app_dir / "settings.json"
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.settings = self._load_settings()
        self.events = queue.Queue()
        self.busy = False
        self.window = tk.Tk()
        self.window.title("Unsupervised Adults MC")
        self.window.geometry("900x635")
        self.window.minsize(780, 590)
        self.window.configure(bg=BG)
        self._make_ui()
        self.window.after(100, self._pump)
        self.log("Minecraft 1.21.1  •  Fabric  •  Auto-updating modpack")
        self.log("First time? Click 'MICROSOFT LOGIN' once, then 'PLAY SMP'.")
        self.log("Only compatible, verified mods are installed. Missing mods are reported.")

    def _load_settings(self):
        try:
            s = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return s if isinstance(s, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_settings(self, *_):
        address = self.server_var.get().strip()
        if len(address) > 253 or any(x in address for x in " /\\\r\n\t"):
            messagebox.showerror("Invalid server", "Use only a host name or IP, optionally followed by :port.")
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
        hero.pack(fill=tk.X, pady=(24, 18))
        tk.Label(hero, text="YOUR WORLD. ONE CLICK AWAY.", fg=TEXT, bg=PANEL,
                 font=("Segoe UI Semibold", 17, "bold")).pack(anchor="w")
        tk.Label(hero, text="Automatic downloads  •  Fabric 1.21.1  •  Verified mod updates", fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(5, 16))
        self.play = tk.Button(hero, text="▶  PLAY SMP", command=self.play_click, bg=PURPLE, fg="#140c22",
                              activebackground="#b792f0", activeforeground="#140c22", relief=tk.FLAT,
                              borderwidth=0, cursor="hand2", font=("Segoe UI", 15, "bold"), pady=12)
        self.play.pack(fill=tk.X)
        tk.Label(hero, text="First launch installs Prism, Minecraft, Fabric and your compatible mods.",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

        settings = tk.Frame(root, bg=BG)
        settings.pack(fill=tk.X)
        tk.Label(settings, text="SMP SERVER", fg=BLUE, bg=BG,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.server_var = tk.StringVar(value=self.settings.get("server_address", ""))
        self.server_entry = tk.Entry(settings, textvariable=self.server_var, bg=PANEL_ALT, fg=TEXT,
                                     insertbackground=TEXT, relief=tk.FLAT, font=("Segoe UI", 11), bd=10)
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 10))
        self.server_entry.bind("<Return>", lambda _: self._save_settings())
        self.save_btn = tk.Button(settings, text="SAVE", command=self._save_settings, bg=PANEL_ALT,
                                  fg=TEXT, relief=tk.FLAT, activebackground="#4a385e", cursor="hand2",
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        self.save_btn.pack(side=tk.RIGHT)

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(fill=tk.X, pady=(18, 15))
        opts = [("MICROSOFT LOGIN", self.login_click), ("CHECK / REPAIR MODS", self.update_click),
                ("OPEN MODS FOLDER", self.folder_click)]
        self.small_buttons = []
        for label, action in opts:
            button = tk.Button(buttons, text=label, command=action, bg=PANEL_ALT, fg=TEXT,
                               activebackground="#4a385e", activeforeground=TEXT, relief=tk.FLAT,
                               font=("Segoe UI", 9, "bold"), cursor="hand2", pady=11, padx=8)
            button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            self.small_buttons.append(button)

        status_frame = tk.Frame(root, bg=BG)
        status_frame.pack(fill=tk.X, pady=(2, 5))
        self.status_var = tk.StringVar(value="READY")
        tk.Label(status_frame, textvariable=self.status_var, fg=BLUE, bg=BG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("UA.Horizontal.TProgressbar", background=PURPLE, troughcolor=PANEL_ALT, bordercolor=PANEL_ALT,
                        lightcolor=PURPLE, darkcolor=PURPLE)
        self.bar = ttk.Progressbar(root, mode="determinate", maximum=100, style="UA.Horizontal.TProgressbar")
        self.bar.pack(fill=tk.X, pady=(0, 12))

        self.console = tk.Text(root, bg="#120e19", fg="#cfc4dd", relief=tk.FLAT, state=tk.DISABLED,
                               wrap=tk.WORD, font=("Consolas", 9), height=8, bd=12, selectbackground="#5c437f")
        self.console.pack(fill=tk.BOTH, expand=True)
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X, pady=(12, 0))
        tk.Label(footer, text="Account sign-in is handled by official Prism Launcher.", fg=MUTED,
                 bg=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        link = tk.Label(footer, text="PROJECT ON GITHUB", fg=BLUE, bg=BG, cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side=tk.RIGHT)
        link.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/TechX1320/UnsupervisedAdultsMC"))

    def log(self, message: str):
        self.console.configure(state=tk.NORMAL)
        self.console.insert(tk.END, str(message) + "\n")
        self.console.see(tk.END)
        self.console.configure(state=tk.DISABLED)

    def _emit(self, kind, value=None):
        self.events.put((kind, value))

    def _pump(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log(value)
                    self.status_var.set(value[:90])
                elif kind == "progress":
                    self.bar["value"] = value * 100
                elif kind == "error":
                    self.status_var.set("INSTALL / UPDATE FAILED")
                    self.log("ERROR: " + value)
                    messagebox.showerror("Unsupervised Adults MC", value)
                elif kind == "complete":
                    self.busy = False
                    for button in [self.play, *self.small_buttons]:
                        button.configure(state=tk.NORMAL)
                    if value:
                        self.status_var.set("UP TO DATE / READY TO PLAY")
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
            success = False
            try:
                task()
                success = True
            except Exception as ex:
                self._emit("error", f"{type(ex).__name__}: {ex}")
            finally:
                self._emit("complete", success)
        threading.Thread(target=worker, daemon=True).start()

    def _prism(self):
        exe = core.ensure_prism(self.app_dir, lambda s: self._emit("log", s))
        data_dir = self.app_dir / "prism-data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return exe, data_dir

    def login_click(self):
        def task():
            exe, data_dir = self._prism()
            self._emit("log", "Prism opened. Choose Accounts → Add Microsoft account (first time only).")
            subprocess.Popen([str(exe), "-d", str(data_dir)], cwd=exe.parent)
        self._run(task)

    def update_click(self):
        self._run(lambda: self._sync(launch=False))

    def play_click(self):
        if not self._save_settings():
            return
        self._run(lambda: self._sync(launch=True))

    def _sync(self, launch: bool):
        status = lambda s: self._emit("log", s)
        exe, data_dir = self._prism()
        catalog = core.get_remote_catalog(status)
        lock = core.load_lock(catalog, self.app_dir, status)
        if core.unresolved_required(lock):
            raise RuntimeError("Required mods missing: " + ", ".join(core.unresolved_required(lock)) +
                               ". Ask the pack owner to fix pack/catalog.json.")
        instance = core.ensure_instance(self.app_dir, catalog)
        result = core.install_client(lock, instance, status, lambda value: self._emit("progress", value))
        warnings = core.manual_warnings(lock) + result["failed"]
        status(f"Pack synced: {result['count']} files, {result['updated']} updated, {len(warnings)} unavailable/manual.")
        if warnings:
            status("Some optional mods are unavailable or need manual installation:")
            for item in warnings:
                status("  - " + item["name"] + ": " + item.get("reason", "Unavailable"))
            (instance / "ua-missing-mods.txt").write_text("\n".join(
                f"{x['name']} - {x.get('reason', '')}\n{x.get('page', '')}" for x in warnings) + "\n", encoding="utf-8")
        if launch:
            cmd = [str(exe), "-d", str(data_dir), "--launch", core.PACK_ID]
            server = self.settings.get("server_address") or catalog.get("server_address", "")
            if server:
                cmd.extend(["--server", server])
            else:
                status("No server address configured; Minecraft will open its main menu.")
            status("Launching Minecraft through Prism. Sign into Microsoft there if prompted.")
            subprocess.Popen(cmd, cwd=exe.parent)

    def folder_click(self):
        folder = self.app_dir / "prism-data" / "instances" / core.PACK_ID / ".minecraft" / "mods"
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            self.log("Mods folder: " + str(folder))

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    Launcher().run()
