"""Prepare a Crafty-importable Fabric server archive for Unsupervised SMP.

The custom launcher runs this in a background thread. It downloads server and
shared Fabric mods from the same SHA-verified lock as the client, fetches the
pinned executable Fabric server launcher from Fabric's official endpoint, and
places the files at the archive root for Crafty's Import ZIP workflow.

Never starts a server, accepts Minecraft's EULA, accesses Crafty or includes
world files, credentials, client-only mods, resource packs or shaders.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zipfile import BadZipFile, ZipFile, ZIP_STORED

import ua_core as core

# Installer version is pinned, not automatically advanced when a new one ships.
FABRIC_INSTALLER_VERSION = "1.1.2"
FABRIC_JAR_NAME = "fabric-server-launch.jar"
FABRIC_MAX_BYTES = 32 * 1024 * 1024


class ServerBuildError(RuntimeError):
    pass


class FabricRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urlparse(newurl)
        if u.scheme != "https" or u.hostname not in {"meta.fabricmc.net", "maven.fabricmc.net"}:
            raise ServerBuildError("Refusing unexpected Fabric download redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fabric_server_url(catalog: dict) -> str:
    core.check_catalog(catalog)
    game, loader = catalog["minecraft_version"], catalog["fabric_loader_version"]
    return (f"https://meta.fabricmc.net/v2/versions/loader/{game}/{loader}/"
            f"{FABRIC_INSTALLER_VERSION}/server/jar")


def valid_server_jar(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size > FABRIC_MAX_BYTES:
            return False
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            return ("META-INF/MANIFEST.MF" in names and
                    any(p.endswith(".class") for p in names))
    except (OSError, BadZipFile, ValueError):
        return False


def download_fabric_jar(url: str, target: Path) -> None:
    """Retrieve only from Fabric's own HTTPS versioned server-jar endpoint."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "meta.fabricmc.net" or not re.fullmatch(
            r"/v2/versions/loader/1\.21\.1/[0-9.]+/[0-9.]+/server/jar", parsed.path):
        raise ServerBuildError("Untrusted Fabric server launcher URL")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".uadownload")
    temp.unlink(missing_ok=True)
    opener = build_opener(FabricRedirect())
    try:
        req = Request(url, headers={"User-Agent": core.UA, "Accept": "application/java-archive"})
        with opener.open(req, timeout=90) as remote, temp.open("wb") as out:
            total = 0
            for block in iter(lambda: remote.read(128 * 1024), b""):
                total += len(block)
                if total > FABRIC_MAX_BYTES:
                    raise ServerBuildError("Fabric launcher download exceeded size limit")
                out.write(block)
        if not valid_server_jar(temp):
            raise ServerBuildError("Official Fabric download was not a valid runnable JAR")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def default_server_properties(port: int = 25565) -> str:
    if not 1 <= int(port) <= 65535:
        raise ValueError("Invalid server port")
    return ("# Unsupervised SMP - edit in Crafty after importing if necessary.\n"
            "# Java 21, Minecraft 1.21.1, Fabric server.\n"
            "level-name=UnsupervisedSMP\n"
            "motd=Unsupervised SMP | Chaos, Adventure and Questionable Decisions\n"
            f"server-port={int(port)}\n"
            "online-mode=true\n"
            "white-list=true\n"
            "enforce-whitelist=true\n"
            "enable-rcon=false\n"
            "enable-command-block=false\n"
            "require-resource-pack=false\n"
            "resource-pack=\n"
            "resource-pack-sha1=\n")


def _server_mods(lock: dict) -> list[dict]:
    return sorted((entry for entry in lock["files"]
                   if entry.get("side") in ("both", "server") and
                   entry.get("path", "").startswith("mods/")),
                  key=lambda entry: entry["path"].lower())


def build_server_zip(root: Path, catalog: dict, lock: dict, status=print,
                     progress=None, fetch_mod=None, fetch_fabric=None) -> Path:
    """Create a root-level Fabric 1.21.1 Crafty import ZIP beside the launcher.

    Uses previously verified mod jars whenever possible. Does not include extra
    unlisted jars, and never deletes manually installed files. Required failures
    abort before publishing the archive; optional failures are reported.
    """
    root = Path(root)
    core.check_catalog(catalog)
    core.validate_lock(lock, catalog)
    if lock.get("fabric_loader_version") != catalog["fabric_loader_version"]:
        raise ServerBuildError("The modpack lock has the wrong Fabric Loader version")
    unresolved = core.unresolved_required(lock, side="server")
    if unresolved:
        raise ServerBuildError("Required server mods are unavailable: " + ", ".join(unresolved))
    entries = _server_mods(lock)
    if not entries:
        raise ServerBuildError("There are no server mods in the selected modpack")
    if fetch_mod is None:
        fetch_mod = core.download_verified
    if fetch_fabric is None:
        fetch_fabric = download_fabric_jar

    setup = root / "Server Setup"
    mods = setup / "mods"
    for folder in (setup, mods):
        if folder.exists() and folder.is_symlink():
            raise ServerBuildError("Refusing to write through a linked server folder")
        folder.mkdir(parents=True, exist_ok=True)

    launcher = setup / FABRIC_JAR_NAME
    url = fabric_server_url(catalog)
    status("Preparing official Fabric 1.21.1 server launcher...")
    if not valid_server_jar(launcher):
        fetch_fabric(url, launcher)
    if not valid_server_jar(launcher):
        raise ServerBuildError("Could not validate Fabric server launcher")
    if progress:
        progress(.12)

    included: list[dict] = []
    failed: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="crafty-mods-", dir=setup) as workdir:
        temp = Path(workdir)
        queued: list[tuple[Path, Path]] = []
        for idx, entry in enumerate(entries, 1):
            # validate_lock limits paths to a single safe file below mods/.
            filename = entry["path"].split("/", 1)[1]
            target = mods / filename
            if target.is_symlink():
                raise ServerBuildError("Refusing to follow a linked server mod: " + filename)
            status(f"Server mod {idx}/{len(entries)}: {entry['name']}")
            if not core.matches(target, entry["hashes"]):
                candidate = temp / filename
                try:
                    fetch_mod(entry["url"], candidate, entry["hashes"])
                    if not core.matches(candidate, entry["hashes"]):
                        raise ServerBuildError("Checksum mismatch: " + filename)
                except (OSError, ValueError, TimeoutError, ServerBuildError) as exc:
                    if entry.get("required", False):
                        raise ServerBuildError(f"Required server mod {entry['name']} could not be downloaded: {exc}") from exc
                    status(f"Optional skipped: {entry['name']}: {exc}")
                    failed.append({"name": entry["name"], "reason": str(exc), "url": entry["url"]})
                    continue
                queued.append((candidate, target))
            included.append(entry)
            if progress:
                progress(.12 + .80 * idx / len(entries))

        # After all required downloads succeed, commit verified mods to cache.
        for candidate, target in queued:
            candidate.replace(target)

    skipped = [item for item in lock.get("skipped", []) if item.get("side") in ("both", "server")
               and "Disabled intentionally" not in item.get("reason", "")]
    missing = skipped + failed
    checksum = hashlib.sha256(launcher.read_bytes()).hexdigest()
    import_text = (
        "UNSUPERVISED SMP / CRAFTY ZIP IMPORT\n"
        "================================\n"
        "Minecraft: 1.21.1 | Fabric Loader: " + catalog["fabric_loader_version"] + " | Java: 21\n"
        "Pack version: " + str(lock["pack_version"]) + "\n\n"
        "1. Crafty > Create New Server > Upload Zip Archive > choose this ZIP.\n"
        "2. Select the ZIP root as the server root (not a nested folder).\n"
        "3. Set server executable to fabric-server-launch.jar.\n"
        "4. Use Java 21 and execution command: java -Xms2G -Xmx6G -jar fabric-server-launch.jar nogui\n"
        "5. Review server.properties port, confirm Minecraft's EULA through Crafty on first start.\n"
        "6. Add player accounts in Crafty console: whitelist add PlayerName\n"
        "7. Keep online-mode=true, white-list=true, enforce-whitelist=true.\n\n"
        "This is a NEW server package. No world, EULA acceptance, or credentials are included.\n"
        "The Fabric launcher downloads official Minecraft/Fabric dependencies when first started.\n"
        "Worldgen mods need a fresh world. Back up any existing server before replacing files.\n"
        "Server resource packs require a separate public HTTPS ZIP URL, not a server mods JAR.\n\n"
        f"Fabric server launcher SHA256: {checksum}\n"
        f"Fabric source: {url}\n\n"
        f"Included server mods: {len(included)}. Optional/manual or unavailable: {len(missing)}.\n"
        "See UNAVAILABLE-MODS.txt inside this archive.\n"
    )
    missing_text = "\n\n".join(f"{item['name']}: {item.get('reason','Unavailable')}\n"
                                 f"{item.get('url', item.get('page',''))}" for item in missing)
    if not missing_text:
        missing_text = "No missing server mods were reported.\n"

    filename = f"UnsupervisedSMP-Crafty-{lock['pack_version']}.zip"
    output = setup / filename
    temp_zip = output.with_suffix(output.suffix + ".tmp")
    temp_zip.unlink(missing_ok=True)
    try:
        with ZipFile(temp_zip, "w", ZIP_STORED, allowZip64=True) as bundle:
            bundle.write(launcher, FABRIC_JAR_NAME)
            for entry in included:
                basename = entry["path"].split("/", 1)[1]
                jar = mods / basename
                if not core.matches(jar, entry["hashes"]):
                    raise ServerBuildError("Cached JAR changed during packaging: " + basename)
                bundle.write(jar, "mods/" + basename)
            bundle.writestr("server.properties", default_server_properties())
            bundle.writestr("CRAFTY-IMPORT.txt", import_text)
            bundle.writestr("UNAVAILABLE-MODS.txt", missing_text)
        temp_zip.replace(output)
    finally:
        temp_zip.unlink(missing_ok=True)

    (setup / "unavailable-mods.txt").write_text(missing_text, encoding="utf-8")
    status(f"Crafty ZIP created: {output} ({len(included)} server mods)")
    if missing:
        status(f"WARNING: {len(missing)} optional/manual server mods are unavailable. Review UNAVAILABLE-MODS.txt.")
    if progress:
        progress(1.0)
    return output
