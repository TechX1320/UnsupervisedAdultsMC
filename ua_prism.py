"""Portable Prism backend for the Unsupervised Adults SMP launcher.

Only the official, SHA-256-pinned Prism portable archive is installed. Prism
manages Microsoft accounts, Minecraft, Fabric, and Java; we manage the modpack.
All persistent files are placed beside our EXE, not in the user's .minecraft.
"""
from __future__ import annotations

import json
import shutil
import stat
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import ua_core as core

PRISM_VERSION = "11.1.1"
PRISM_URL = (
    "https://github.com/PrismLauncher/PrismLauncher/releases/download/11.1.1/"
    "PrismLauncher-Windows-MinGW-w64-Portable-11.1.1.zip"
)
PRISM_SHA256 = "05841d0b3bfc0a8212658457cc6035e1c29cd7ffae919464e874e384cbe8d062"
PRISM_MAX_DOWNLOAD = 100 * 1024 * 1024
PRISM_MAX_UNPACK = 650 * 1024 * 1024


def data_dir(root: Path) -> Path:
    return root / "prism-data"


def prism_exe(root: Path) -> Path | None:
    folder = root / "prism-bin"
    if not folder.is_dir():
        return None
    # The official ZIP's top-level folder is not considered a stable API.
    for candidate in folder.rglob("*"):
        if candidate.is_file() and candidate.name.lower() == "prismlauncher.exe":
            return candidate
    return None


def _unpack_verified(archive: Path, staging: Path) -> None:
    """Reject zip-slip, symlinks, pathological archives before extraction."""
    with ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > 15000 or sum(x.file_size for x in entries) > PRISM_MAX_UNPACK:
            raise ValueError("Prism archive exceeds safety limits")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (not entry.filename or path.is_absolute() or ".." in path.parts or
                    "\\" in entry.filename or ":" in entry.filename):
                raise ValueError("Prism archive contains an unsafe path")
            if stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError("Prism archive contains a symlink")
            target = (staging / entry.filename).resolve()
            if not target.is_relative_to(staging.resolve()):
                raise ValueError("Prism archive tries to write outside its folder")
        bundle.extractall(staging)


def ensure_prism(root: Path, status=print, fetch=core.download_verified) -> Path:
    existing = prism_exe(root)
    if existing is not None:
        return existing
    root.mkdir(parents=True, exist_ok=True)
    staging = root / "prism-extract.tmp"
    target = root / "prism-bin"
    archive = root / "prism-download.zip"
    status("Installing official Prism Launcher Portable (one-time, ~44 MB)...")
    shutil.rmtree(staging, ignore_errors=True)
    try:
        fetch(PRISM_URL, archive, {"sha256": PRISM_SHA256}, status, max_bytes=PRISM_MAX_DOWNLOAD)
        staging.mkdir(parents=True)
        _unpack_verified(archive, staging)
        extracted = next((x for x in staging.rglob("*") if x.is_file() and x.name.lower() == "prismlauncher.exe"), None)
        if extracted is None:
            raise ValueError("The verified Prism ZIP did not contain its executable")
        if target.exists():
            # Only happens for a partial/corrupt previous installation.
            shutil.rmtree(target)
        staging.replace(target)
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
    exe = prism_exe(root)
    if exe is None:
        raise RuntimeError("Prism was downloaded but its executable is missing")
    status("Prism Launcher installed inside UnsupervisedAdultsMC_Data.")
    return exe


def ensure_instance(root: Path, catalog: dict) -> Path:
    """Create (or repair) only the metadata of our dedicated Prism instance."""
    core.check_catalog(catalog)
    instance = data_dir(root) / "instances" / core.PACK_ID
    instance.mkdir(parents=True, exist_ok=True)
    cfg = instance / "instance.cfg"
    meta = instance / "mmc-pack.json"
    if not cfg.is_file():
        cfg.write_text(
            "[General]\nConfigVersion=1.2\nInstanceType=OneSix\n"
            "name=Unsupervised SMP\niconKey=default\n",
            encoding="utf-8",
        )
    elif cfg.is_file():
        # Rename only the old default title; keep players' custom names intact.
        old_cfg = cfg.read_text(encoding="utf-8")
        if "name=Unsupervised Adults SMP\n" in old_cfg:
            cfg.write_text(old_cfg.replace("name=Unsupervised Adults SMP\n",
                                           "name=Unsupervised SMP\n"), encoding="utf-8")
    if not meta.is_file():
        meta.write_text(json.dumps({
            "formatVersion": 1,
            "components": [
                {"uid": "net.minecraft", "version": catalog["minecraft_version"], "important": True},
                {"uid": "net.fabricmc.fabric-loader", "version": catalog["fabric_loader_version"]},
            ],
        }, indent=2) + "\n", encoding="utf-8")
    (instance / ".minecraft").mkdir(exist_ok=True)
    return instance


def migrate_legacy(root: Path, instance: Path, status=print) -> int:
    """Move older custom-launcher user files to Prism without copying game assets.

    Never deletes older Minecraft/Java installations or overwrites existing saves,
    configs or resource packs. A marker prevents repeated migrations.
    """
    marker = root / "prism-data" / ".ua-migrated"
    source = root / "instance" / ".minecraft"
    if marker.is_file() or not source.is_dir():
        return 0
    dest = instance / ".minecraft"
    dest.mkdir(parents=True, exist_ok=True)
    folders = ("mods", "resourcepacks", "shaderpacks", "config", "saves", "screenshots")
    files = ("options.txt", "servers.dat", "optionsof.txt", "optionsshaders.txt")
    migrated = 0
    for name in (*folders, *files):
        old = source / name
        new = dest / name
        if not old.exists() or old.is_symlink():
            continue
        if not new.exists():
            shutil.move(str(old), str(new))
            migrated += 1
            continue
        if old.is_dir() and new.is_dir():
            # Move nonconflicting files recursively; never overwrite Prism content.
            for src in list(old.rglob("*")):
                if not src.is_file() or src.is_symlink():
                    continue
                dest_file = new / src.relative_to(old)
                if not dest_file.exists():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest_file))
                    migrated += 1
    for name in ("ua-managed.json", "ua-missing-mods.txt"):
        old = root / "instance" / name
        new = instance / name
        if old.is_file() and not new.exists():
            shutil.move(str(old), str(new))
            migrated += 1
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("Migrated user content from the former direct-launch instance.\n", encoding="utf-8")
    if migrated:
        status(f"Moved {migrated} existing settings/mods/world items to Prism, without making extra copies.")
    status("Old Minecraft runtime files may remain in Data/instance; remove them manually only after testing Prism.")
    return migrated


def accounts_file(root: Path) -> Path:
    # Prism's own account file. Never read its tokens or copy it elsewhere.
    return data_dir(root) / "accounts.json"


def has_prism_account_file(root: Path) -> bool:
    return accounts_file(root).is_file()


def _prism_command(root: Path, exe: Path) -> list[str]:
    return [str(exe), "-d", str(data_dir(root))]


def open_prism(root: Path, exe: Path, popen=subprocess.Popen):
    data_dir(root).mkdir(parents=True, exist_ok=True)
    return popen(_prism_command(root, exe), cwd=exe.parent)


def validate_server_address(address: str) -> str:
    value = (address or "").strip()
    if not value:
        return ""
    if len(value) > 253 or any(c in value for c in " /\\\r\n\t\0"):
        raise ValueError("Enter a host/IP with optional :port (no spaces)")
    if value.startswith("["):
        host, sep, end = value[1:].partition("]")
        if not sep or not host or (end and not end.startswith(":")):
            raise ValueError("IPv6 servers need [address]:port")
        port = end[1:] if end else ""
    elif value.count(":") > 1:
        raise ValueError("IPv6 servers need [address]:port")
    elif ":" in value:
        host, port = value.rsplit(":", 1)
    else:
        host, port = value, ""
    if not host or (port and (not port.isdigit() or not 1 <= int(port) <= 65535)):
        raise ValueError("Enter a valid server host and port")
    if value.endswith(":"):
        raise ValueError("Port cannot be empty")
    return value


def launch_instance(root: Path, exe: Path, server: str = "", popen=subprocess.Popen):
    if not (data_dir(root) / "instances" / core.PACK_ID / "mmc-pack.json").is_file():
        raise RuntimeError("Prism SMP instance was not created")
    command = _prism_command(root, exe) + ["--launch", core.PACK_ID]
    addr = validate_server_address(server)
    if addr:
        command.extend(["--server", addr])
    return popen(command, cwd=exe.parent)
