"""Verified, private Java 21 fallback when the Mojang runtime cannot be found.

Downloads Eclipse Temurin JRE from Adoptium metadata. A SHA-256 checksum is
verified before extraction, and everything remains inside the game directory.
"""
from __future__ import annotations

import re
import shutil
import stat
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from zipfile import ZipFile, BadZipFile

import ua_core as core

TEMURIN_METADATA = (
    "https://api.adoptium.net/v3/assets/latest/21/hotspot"
    "?architecture=x64&image_type=jre&os=windows&vendor=eclipse"
)


class JavaInstallError(RuntimeError):
    pass


def _safe_extract(archive: Path, out: Path) -> Path:
    """Extract a single JRE tree, rejecting traversals, symlinks and zip bombs."""
    with ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > 700 * 1024 * 1024:
            raise JavaInstallError("Java archive exceeds safety limits")
        for item in infos:
            pure = PurePosixPath(item.filename)
            if (not item.filename or pure.is_absolute() or ".." in pure.parts
                    or "\\" in item.filename or ":" in item.filename):
                raise JavaInstallError("Unsafe Java archive entry")
            if stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK:
                raise JavaInstallError("Java archive contains a symlink")
        exe_paths = [PurePosixPath(i.filename) for i in infos
                     if i.filename.lower().endswith("/bin/java.exe")]
        if len(exe_paths) != 1:
            raise JavaInstallError("Java archive does not contain exactly one Java executable")
        z.extractall(out)
    candidate = out.joinpath(*exe_paths[0].parts)
    if not candidate.is_file() or not candidate.resolve().is_relative_to(out.resolve()):
        raise JavaInstallError("Java archive executable not found after extraction")
    return candidate.parent.parent


def ensure_temurin_java(game: Path, status=print, fetch=core.download_verified,
                        get_json=core.get_json) -> str:
    """Return self-contained Windows Java 21 executable, downloading if needed."""
    runtime = game / "runtime"
    target = runtime / "ua-temurin21"
    java = target / "bin" / "java.exe"
    if java.is_file():
        return str(java)
    status("Mojang Java runtime not found; installing portable Eclipse Temurin 21...")
    try:
        data = get_json(TEMURIN_METADATA)
        package = data[0]["binary"]["package"]
        url, sha = package["link"], package["checksum"]
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != "github.com"
                or not re.fullmatch(r"[0-9a-fA-F]{64}", sha)):
            raise JavaInstallError("Untrusted Java download metadata")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        if isinstance(exc, JavaInstallError):
            raise
        raise JavaInstallError("Could not read trusted Temurin Java metadata") from exc

    runtime.mkdir(parents=True, exist_ok=True)
    archive = runtime / "ua-temurin21-download.zip"
    unpack = runtime / "ua-temurin21-extract"
    prepared = runtime / "ua-temurin21-new"
    try:
        fetch(url, archive, {"sha256": sha}, status)
        shutil.rmtree(unpack, ignore_errors=True)
        unpack.mkdir()
        root = _safe_extract(archive, unpack)
        if prepared.exists():
            shutil.rmtree(prepared)
        shutil.move(str(root), str(prepared))
        if not (prepared / "bin" / "java.exe").is_file():
            raise JavaInstallError("Downloaded Java runtime is incomplete")
        if target.exists():
            shutil.rmtree(target)
        prepared.replace(target)
        status("Portable Temurin Java 21 installed successfully.")
        return str(java)
    except (OSError, BadZipFile, ValueError) as exc:
        raise JavaInstallError(f"Could not install Java 21: {exc}") from exc
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(unpack, ignore_errors=True)
        if prepared.exists():
            shutil.rmtree(prepared, ignore_errors=True)
