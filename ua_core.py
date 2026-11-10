"""Verified Modrinth/GitHub modpack downloads for the dedicated Prism SMP instance.

All game and authentication work is delegated to official Prism Launcher.
This file does not read or store Microsoft account tokens.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

LAUNCHER_NAME = "Unsupervised Adults SMP"
PACK_ID = "UnsupervisedAdultsSMP"
REPO_ROOT = "https://raw.githubusercontent.com/TechX1320/UnsupervisedAdultsMC/main/pack/"
UA = "TechX1320/UnsupervisedAdultsMC/0.3 (+https://github.com/TechX1320/UnsupervisedAdultsMC)"
FOLDERS = {"mod": "mods", "resourcepack": "resourcepacks", "shader": "shaderpacks"}
FILE_EXT = {"mod": (".jar",), "resourcepack": (".zip",), "shader": (".zip",)}


def app_root() -> Path:
    # Frozen: place all persistent data next to the distributed EXE.
    # Source tree: keep an identically structured data folder next to the code.
    location = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    return location / "UnsupervisedAdultsMC_Data"


def bundled_catalog_path() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "pack" / "catalog.json"


def canonical_sha(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_json(url: str, timeout: int = 25) -> dict | list:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get_remote_catalog(status=print) -> dict:
    try:
        data = get_json(REPO_ROOT + "catalog.json")
        check_catalog(data)
        return data
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        status(f"Could not reach GitHub catalog; using bundled copy ({exc}).")
        data = json.loads(bundled_catalog_path().read_text(encoding="utf-8"))
        check_catalog(data)
        return data


def check_catalog(catalog: dict) -> None:
    if catalog.get("schema") != 1 or catalog.get("minecraft_version") != "1.21.1":
        raise ValueError("Unexpected catalog schema or Minecraft version")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", catalog.get("fabric_loader_version", "")):
        raise ValueError("Invalid Fabric Loader version")
    # The pinned 1.21.1 modpack has Fabric Loader >=0.19.5 dependencies
    # (notably Fabric Language Kotlin); never silently ship a lower version.
    if tuple(map(int, catalog["fabric_loader_version"].split("."))) < (0, 19, 5):
        raise ValueError("Unsupervised SMP requires Fabric Loader 0.19.5 or newer")
    if not isinstance(catalog.get("mods"), list):
        raise ValueError("Catalog mods must be a list")


def _safe_filename(name: str, extensions: tuple[str, ...]) -> str:
    if not isinstance(name, str) or len(name) > 160 or name in {".", ".."}:
        raise ValueError("Unacceptable file name")
    if "/" in name or "\\" in name or ":" in name or name.startswith("."):
        raise ValueError("Unsafe filename: " + str(name))
    if not name.lower().endswith(extensions):
        raise ValueError("Unexpected file type: " + name)
    return name


def _file_url(url: str) -> bool:
    p = urllib.parse.urlparse(url)
    return p.scheme == "https" and p.hostname in ("cdn.modrinth.com", "github.com")


def _version_query(project: str, kind: str, mc: str) -> str:
    loaders = ["fabric"] if kind == "mod" else ["iris", "minecraft"] if kind == "shader" else ["minecraft"]
    args = urllib.parse.urlencode({"game_versions": json.dumps([mc]), "loaders": json.dumps(loaders)})
    return f"https://api.modrinth.com/v2/project/{urllib.parse.quote(project, safe='')}/version?{args}"


def _select_version(versions: list, kind: str, mc: str) -> dict:
    if not versions and kind == "shader":
        raise LookupError("No Iris-compatible shader release")
    eligible = [v for v in versions if mc in v.get("game_versions", [])]
    if not eligible:
        raise LookupError("No Minecraft " + mc + " version")
    # Prefer released builds, then newest within that channel. Do not select older alpha over stable.
    rank = {"release": 2, "beta": 1, "alpha": 0}
    return max(eligible, key=lambda v: (rank.get(v.get("version_type"), -1), v.get("date_published", "")))


def _chosen_file(version: dict, kind: str) -> dict:
    files = version.get("files", [])
    usable = [f for f in files if str(f.get("filename", "")).lower().endswith(FILE_EXT[kind]) and _file_url(f.get("url", ""))]
    if not usable:
        raise LookupError("No permitted downloadable file")
    return next((f for f in usable if f.get("primary")), usable[0])


def resolve_catalog(catalog: dict, status=print, api=get_json) -> dict:
    """Resolve exactly compatible versions and required transitive dependencies.

    Some projects deliberately have no compatible versions; they are reported as
    skipped, not mislabeled as installed. For deterministic group updates, run
    update_pack.cmd and commit the generated pack-lock.json to main.
    """
    check_catalog(catalog)
    minecraft = catalog["minecraft_version"]
    files: list[dict] = []
    skipped: list[dict] = []
    resolved_ids: dict[str, dict] = {}
    aliases: dict[str, str] = {}
    environments: dict[str, str] = {}
    outcomes: dict[str, bool] = {}
    visiting: set[str] = set()

    def side_for_env(requested: str, env: str) -> str:
        if env in ("server_only", "dedicated_server_only"):
            return "server"
        if env in ("client_only", "singleplayer_only"):
            return "client"
        return requested

    def promote(entry: dict, requested_side: str, required: bool) -> None:
        # A library can first be discovered by a client-only mod, then required
        # by a shared/server mod. Preserve both use cases in the lock file.
        old = entry["side"]
        entry["side"] = old if old == requested_side else "both"
        entry["required"] = entry.get("required", False) or required

    def resolve(name: str, project: str, kind: str, side: str, required: bool, *, version_id: str | None = None) -> bool:
        key = version_id or project
        if key in outcomes:
            if outcomes[key] and key in aliases:
                ident = aliases[key]
                promote(resolved_ids[ident], side_for_env(side, environments[ident]), required)
            return outcomes[key]
        if key in visiting:
            return True  # cycle guard for unusual dependency metadata
        visiting.add(key)
        try:
            if version_id:
                v = api("https://api.modrinth.com/v2/version/" + urllib.parse.quote(version_id, safe=""))
                if minecraft not in v.get("game_versions", []) or kind == "mod" and "fabric" not in v.get("loaders", []):
                    raise LookupError("Required dependency not compatible with 1.21.1 Fabric")
            else:
                versions = api(_version_query(project, kind, minecraft))
                v = _select_version(versions, kind, minecraft)
            ident = v.get("project_id", project)
            if ident in resolved_ids:
                promote(resolved_ids[ident], side_for_env(side, environments[ident]), required)
                aliases[key] = ident
                outcomes[key] = True
                return True
            asset = _chosen_file(v, kind)
            filename = _safe_filename(asset["filename"], FILE_EXT[kind])
            hashes = asset.get("hashes", {})
            if not any(hashes.get(x) for x in ("sha512", "sha256", "sha1")):
                raise LookupError("No file checksum")
            env = v.get("environment", "client_and_server")
            if env in ("server_only", "dedicated_server_only") and side == "client":
                raise LookupError("Only available for dedicated servers")
            if env in ("client_only", "singleplayer_only") and side == "server":
                raise LookupError("Only available on clients")
            actual_side = side
            if env in ("client_only", "singleplayer_only"):
                actual_side = "client"
            elif env in ("server_only", "dedicated_server_only"):
                actual_side = "server"
            if kind == "mod":
                for dependency in v.get("dependencies", []):
                    if dependency.get("dependency_type") != "required":
                        continue
                    dep_id = dependency.get("project_id") or dependency.get("version_id")
                    if not dep_id:
                        continue
                    good = resolve("Dependency: " + dep_id, dependency.get("project_id") or dep_id,
                                   "mod", actual_side, required, version_id=dependency.get("version_id"))
                    if not good:
                        raise LookupError("Required dependency " + dep_id + " is unavailable")
            entry = {
                "name": name,
                "project_id": ident,
                "version_id": v.get("id", ""),
                "version": v.get("version_number", ""),
                "side": actual_side,
                "path": f"{FOLDERS[kind]}/{filename}",
                "url": asset["url"],
                "size": asset.get("size", 0),
                "hashes": {h: hashes[h] for h in ("sha512", "sha256", "sha1") if hashes.get(h)},
                "required": required
            }
            files.append(entry)
            resolved_ids[ident] = entry
            environments[ident] = env
            aliases[key] = ident
            outcomes[key] = True
            status(f"Found {name} ({entry['version']})")
            return True
        except (KeyError, TypeError, ValueError, LookupError, urllib.error.URLError, TimeoutError) as exc:
            skipped.append({"name": name, "page": f"https://modrinth.com/{'mod' if kind == 'mod' else kind}/{project}",
                            "reason": str(exc), "required": required, "side": side})
            outcomes[key] = False
            status(f"Unavailable: {name}: {exc}")
            return False
        finally:
            visiting.discard(key)

    for mod in catalog["mods"]:
        if not mod.get("enabled", True):
            skipped.append({"name": mod["name"], "page": mod.get("page", ""),
                            "reason": "Disabled intentionally in pack catalog", "required": False, "side": mod.get("side", "client")})
            continue
        source = mod.get("source", "modrinth")
        if source == "manual":
            skipped.append({"name": mod["name"], "page": mod.get("page", ""),
                            "reason": mod.get("reason", "Manual installation required"),
                            "required": False, "side": mod.get("side", "client")})
        elif source == "direct":
            kind = mod["type"]
            url = mod.get("url", "")
            if not _file_url(url) or not re.fullmatch(r"[a-fA-F0-9]{64}", mod.get("sha256", "")):
                raise ValueError("Invalid first-party direct asset: " + mod["name"])
            filename = _safe_filename(urllib.parse.unquote(urllib.parse.urlsplit(url).path.split("/")[-1]), FILE_EXT[kind])
            files.append({"name": mod["name"], "side": mod["side"], "path": f"{FOLDERS[kind]}/{filename}",
                          "url": url, "hashes": {"sha256": mod["sha256"]}, "required": mod.get("required", True), "size": 0})
        else:
            resolve(mod["name"], mod["slug"], mod["type"], mod.get("side", "client"), mod.get("required", False))

    # A conflicted filename is a blocker; never silently overwrite one mod with another.
    paths = [f["path"].lower() for f in files]
    if len(paths) != len(set(paths)):
        raise ValueError("Two mods resolve to the same filename. Pin or rename explicitly.")
    return {
        "schema": 1,
        "pack_version": catalog["pack_version"],
        "catalog_sha256": canonical_sha(catalog),
        "minecraft_version": minecraft,
        "fabric_loader_version": catalog["fabric_loader_version"],
        "files": files,
        "skipped": skipped
    }


def validate_lock(lock: dict, catalog: dict) -> None:
    if lock.get("schema") != 1 or lock.get("catalog_sha256") != canonical_sha(catalog):
        raise ValueError("Modpack lock does not match published catalog")
    if lock.get("minecraft_version") != "1.21.1" or not isinstance(lock.get("files"), list):
        raise ValueError("Unrecognized modpack lock")
    seen = set()
    for entry in lock["files"]:
        folder, sep, name = entry.get("path", "").partition("/")
        if sep != "/" or folder not in FOLDERS.values():
            raise ValueError("Unsafe destination path")
        kind = next(k for k, v in FOLDERS.items() if v == folder)
        _safe_filename(name, FILE_EXT[kind])
        if entry["path"].lower() in seen:
            raise ValueError("Duplicate mod filename")
        seen.add(entry["path"].lower())
        if not _file_url(entry.get("url", "")):
            raise ValueError("Unapproved mod download host")
        hashes = entry.get("hashes", {})
        if not any(re.fullmatch(r"[a-fA-F0-9]{" + str(size) + r"}", hashes.get(h, "")) for h, size in (("sha512",128),("sha256",64),("sha1",40))):
            raise ValueError("No valid SHA checksum for " + entry["path"])


def load_lock(catalog: dict, local_cache_dir: Path, status=print, api=get_json) -> dict:
    path = local_cache_dir / "lock-cache.json"
    try:
        lock = get_json(REPO_ROOT + "pack-lock.json")
        validate_lock(lock, catalog)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        status(f"Pinned modpack {lock['pack_version']} loaded from GitHub.")
        return lock
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        status(f"No matching published lock yet ({exc}).")
    if path.exists():
        try:
            lock = json.loads(path.read_text(encoding="utf-8"))
            validate_lock(lock, catalog)
            status("Using cached compatible modpack.")
            return lock
        except (OSError, ValueError):
            pass
    status("Resolving compatible mods from Modrinth. Owner should publish a pinned pack-lock.json.")
    lock = resolve_catalog(catalog, status=status, api=api)
    validate_lock(lock, catalog)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return lock


def unresolved_required(lock: dict, side="client") -> list[str]:
    return [x["name"] for x in lock.get("skipped", [])
            if x.get("required") and x.get("side") in (side, "both")]


def _digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def matches(path: Path, hashes: dict) -> bool:
    if not path.is_file():
        return False
    # Verify the strongest available hash, not all, to avoid extra large-file reads.
    for algorithm in ("sha512", "sha256", "sha1"):
        expected = hashes.get(algorithm)
        if expected:
            return _digest(path, algorithm).lower() == expected.lower()
    return False


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        h = (parsed.hostname or "").lower()
        allowed = h in ("github.com", "cdn.modrinth.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")
        if parsed.scheme != "https" or not allowed:
            raise ValueError("Blocked unexpected file download redirect to " + h)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_verified(url: str, dest: Path, hashes: dict, status=print, max_bytes: int = 512*1024*1024) -> None:
    if not _file_url(url):
        raise ValueError("Blocked download host: " + url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".uadownload")
    tmp.unlink(missing_ok=True)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with opener.open(request, timeout=60) as incoming, tmp.open("wb") as output:
            written = 0
            while True:
                chunk = incoming.read(128 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError("Download unexpectedly large")
                output.write(chunk)
        if not matches(tmp, hashes):
            raise ValueError("Checksum mismatch for " + dest.name)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def install_client(lock: dict, instance: Path, status=print, progress=None) -> dict:
    if unresolved_required(lock):
        raise RuntimeError("Required mods unavailable: " + ", ".join(unresolved_required(lock)))
    game = instance / ".minecraft"
    game.mkdir(parents=True, exist_ok=True)
    state_file = instance / "ua-managed.json"
    previous: set[str] = set()
    if state_file.exists():
        try:
            previous = set(json.loads(state_file.read_text(encoding="utf-8")).get("files", []))
        except (OSError, ValueError):
            previous = set()
    wanted = [f for f in lock["files"] if f.get("side") in ("both", "client")]
    staging = instance / "ua-staging"
    staging.mkdir(parents=True, exist_ok=True)
    staged = []
    succeeded = []
    failed = []
    try:
        for i, entry in enumerate(wanted):
            rel = entry["path"]
            path = game / rel
            if matches(path, entry["hashes"]):
                status(f"OK: {entry['name']} is current")
            else:
                status(f"Downloading {entry['name']} ({i + 1}/{len(wanted)})")
                stage = staging / rel.replace("/", "__")
                try:
                    download_verified(entry["url"], stage, entry["hashes"], status)
                    staged.append((stage, path))
                except (OSError, ValueError, TimeoutError) as exc:
                    if entry.get("required", False):
                        raise RuntimeError(f"Required file {entry['name']} failed to download: {exc}") from exc
                    status(f"Optional download unavailable: {entry['name']}: {exc}")
                    failed.append({"name": entry["name"], "reason": str(exc), "page": entry["url"]})
                    continue
            succeeded.append(entry)
            if progress:
                progress((i + 1) / max(1, len(wanted)))
        for src, dest in staged:
            dest.parent.mkdir(parents=True, exist_ok=True)
            src.replace(dest)
        desired = {entry["path"] for entry in succeeded}
        safe_game_root = game.resolve()
        for name in previous - desired:
            # Never remove files this launcher has not previously installed.
            target = (game / name).resolve()
            if target.is_relative_to(safe_game_root) and target.is_file() and target.parent.name in FOLDERS.values():
                target.unlink()
                status("Removed old managed file: " + name)
        state_file.write_text(json.dumps({"pack_version": lock["pack_version"], "files": sorted(desired)}, indent=2) + "\n", encoding="utf-8")
        return {"count": len(succeeded), "skipped": len(lock.get("skipped", [])), "updated": len(staged), "failed": failed}
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def manual_warnings(lock: dict) -> list[dict]:
    return [x for x in lock.get("skipped", []) if "Disabled intentionally" not in x.get("reason", "")]
