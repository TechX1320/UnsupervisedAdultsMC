"""Merge owner-supplied 1.21.1 resource packs into one vanilla server pack.

This deliberately does NOT download or redistribute copyrighted client packs.
Higher-numbered input ZIP files override lower-numbered ones. Conflicts are logged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "Server Setup" / "resourcepacks" / "input"
OUT_DIR = ROOT / "Server Setup" / "resourcepacks" / "output"
PACK_NAME = "UnsupervisedSMP-ServerResourcePack.zip"
PACK_FORMAT = 34  # Minecraft 1.21 and 1.21.1
MAX_UNCOMPRESSED = 500 * 1024 * 1024
MAX_UPLOAD = 250 * 1024 * 1024


class MergeError(ValueError):
    pass


def _pack_data(path: Path):
    with zipfile.ZipFile(path) as archive:
        try:
            meta = json.loads(archive.read("pack.mcmeta"))
        except (KeyError, ValueError) as exc:
            raise MergeError(f"{path.name} has no readable pack.mcmeta") from exc
        fmt = meta.get("pack", {}).get("pack_format")
        if fmt != PACK_FORMAT:
            raise MergeError(f"{path.name} targets pack format {fmt}; Minecraft 1.21.1 needs {PACK_FORMAT}")
        infos = archive.infolist()
        if len(infos) > 25000:
            raise MergeError("Too many entries in " + path.name)
        unpacked = sum(info.file_size for info in infos)
        if unpacked > MAX_UNCOMPRESSED:
            raise MergeError("Too much uncompressed data in " + path.name)
        return infos


def _validate_info(info: zipfile.ZipInfo, archive: Path) -> str:
    name = info.filename
    pure = PurePosixPath(name)
    if (not name or pure.is_absolute() or ".." in pure.parts or ":" in name
            or "\\" in name or name.startswith("/")):
        raise MergeError(f"Unsafe path in {archive.name}: {name}")
    if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
        raise MergeError("Symlink in pack: " + name)
    if info.file_size > MAX_UPLOAD:
        raise MergeError("Oversized file in pack: " + name)
    return name


def merge(input_dir: Path = IN_DIR, output_dir: Path = OUT_DIR, status=print) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    sources = sorted(input_dir.glob("*.zip"), key=lambda p: p.name.lower())
    if not sources:
        raise MergeError("No resource pack ZIPs found. Add permitted 1.21.1 ZIPs to Server Setup/resourcepacks/input")
    output_dir.mkdir(parents=True, exist_ok=True)
    chosen: dict[str, tuple[Path, str]] = {}
    conflicts: list[str] = []
    ignored: set[str] = set()
    total = 0
    for src in sources:
        for info in _pack_data(src):
            name = _validate_info(info, src)
            if info.is_dir():
                continue
            if name == "pack.mcmeta":
                continue
            if not name.startswith("assets/") and name != "pack.png":
                ignored.add(f"{src.name}: {name}")
                continue
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise MergeError("Input packs exceed the combined 500 MiB expansion limit")
            if name in chosen:
                conflicts.append(f"{name}: {chosen[name][0].name} -> {src.name} (latter wins)")
            chosen[name] = (src, name)
    if not any(name.startswith("assets/") for name in chosen):
        raise MergeError("No assets/ files found. Server resource packs must contain assets, not only data packs")
    target = output_dir / PACK_NAME
    tmp = output_dir / (PACK_NAME + ".partial")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
            manifest = json.dumps({"pack": {"pack_format": PACK_FORMAT,
                           "description": "Unsupervised SMP | official server visuals"}}, indent=2) + "\n"
            output.writestr("pack.mcmeta", manifest)
            for name, (source, arcname) in sorted(chosen.items()):
                with zipfile.ZipFile(source) as reader:
                    with reader.open(arcname) as stream:
                        with output.open(name, "w") as destination:
                            shutil.copyfileobj(stream, destination, length=128 * 1024)
        if tmp.stat().st_size > MAX_UPLOAD:
            raise MergeError("Merged pack exceeds Minecraft's 250 MiB server download cap")
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
    sha1 = hashlib.sha1()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha1.update(chunk)
    checksum = sha1.hexdigest()
    properties = output_dir / "resource-pack.properties"
    properties.write_text(
        "# Host the ZIP on a public HTTPS URL you control (and have permission to distribute).\n"
        "# Paste these settings into Crafty server.properties after replacing the URL.\n"
        "resource-pack=https://YOUR-DOWNLOAD-HOST/UnsupervisedSMP-ServerResourcePack.zip\n"
        f"resource-pack-sha1={checksum}\n"
        "require-resource-pack=false\n", encoding="utf-8")
    report = output_dir / "merge-report.txt"
    report.write_text(
        "Input precedence: alphabetical by ZIP filename; later packs replace earlier files.\n"
        + "Inputs:\n" + "\n".join(x.name for x in sources)
        + "\n\nOverridden paths:\n" + ("\n".join(conflicts) or "(none)")
        + "\n\nIgnored non-assets paths:\n" + ("\n".join(sorted(ignored)) or "(none)")
        + "\n", encoding="utf-8")
    status(f"Merged {len(sources)} packs with {len(chosen)} assets ({len(conflicts)} file overlaps): {target}")
    status("SHA-1: " + checksum)
    status("Review merge-report.txt and resource-pack.properties before distributing.")
    return target


def main():
    try:
        merge()
    except (MergeError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        raise SystemExit("Resource pack merge failed: " + str(exc)) from exc


if __name__ == "__main__":
    main()
