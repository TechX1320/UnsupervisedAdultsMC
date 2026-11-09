"""Install official Minecraft, Mojang Java runtime, Fabric and launch directly.

minecraft-launcher-lib is a small embedded Python library, NOT a separate launcher.
The user only runs our one-file EXE. Game assets are downloaded from official sources.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess


class InstallError(RuntimeError):
    pass


def profile_id(catalog: dict) -> str:
    mc = catalog["minecraft_version"]
    fabric = catalog["fabric_loader_version"]
    return f"fabric-loader-{fabric}-{mc}"


def server_options(address: str) -> dict:
    address = (address or "").strip()
    if not address:
        return {}
    # Minecraft's --server and --port options have separate arguments.
    if address.startswith("["):
        host, separator, suffix = address[1:].partition("]")
        if not separator or not host:
            raise ValueError("Invalid IPv6 server address")
        if suffix and not suffix.startswith(":"):
            raise ValueError("Invalid server port")
        port = suffix[1:] if suffix else ""
    elif address.count(":") == 1:
        host, port = address.rsplit(":", 1)
    elif ":" in address:
        raise ValueError("Use [IPv6-address]:port for IPv6")
    else:
        host, port = address, ""
    if not host or any(c in host for c in "/\\\r\n\t "):
        raise ValueError("Invalid server host")
    if port and (not port.isdecimal() or not 1 <= int(port) <= 65535):
        raise ValueError("Server port must be between 1 and 65535")
    result = {"server": host}
    if port:
        result["port"] = port
    return result


def _vanilla_runtime(game: Path, mc: str, lib, callback) -> str:
    version_json = game / "versions" / mc / f"{mc}.json"
    data = json.loads(version_json.read_text(encoding="utf-8"))
    component = data.get("javaVersion", {}).get("component")
    if not component:
        raise InstallError("Minecraft version metadata does not declare a Java runtime")
    java = lib.runtime.get_executable_path(component, str(game))
    if java and Path(java).is_file():
        return str(java)
    # The Mojang installer may successfully download Java but have a mismatched
    # runtime directory layout. Look only inside this private game's runtime tree.
    runtime_folder = game / "runtime" / component
    if runtime_folder.is_dir():
        for candidate in runtime_folder.rglob("java.exe"):
            if candidate.parent.name.lower() == "bin" and candidate.is_file():
                return str(candidate)
    from ua_java import ensure_temurin_java, JavaInstallError
    try:
        return ensure_temurin_java(game, callback.get("setStatus", print))
    except Exception as exc:
        raise InstallError(f"Minecraft Java 21 installation failed: {exc}") from exc


def ensure_game(game: Path, catalog: dict, status=print, progress=None) -> tuple[str, str]:
    import minecraft_launcher_lib as lib
    game.mkdir(parents=True, exist_ok=True)
    mc, loader = catalog["minecraft_version"], catalog["fabric_loader_version"]
    max_progress = [1]
    def set_progress(value):
        if progress:
            progress(min(1.0, value / max(1, max_progress[0])))
    cb = {
        "setStatus": lambda s: status(str(s)),
        "setProgress": set_progress,
        "setMax": lambda v: max_progress.__setitem__(0, max(1, v)),
    }
    status(f"Installing/repairing Minecraft {mc} (includes the required Java runtime)...")
    lib.install.install_minecraft_version(mc, str(game), callback=cb)
    java = _vanilla_runtime(game, mc, lib, cb)
    fabric_id = profile_id(catalog)
    fabric_profile = game / "versions" / fabric_id / (fabric_id + ".json")
    if not fabric_profile.is_file():
        status(f"Installing Fabric Loader {loader}...")
        lib.fabric.install_fabric(mc, str(game), loader_version=loader, callback=cb, java=java)
    else:
        # Repair a previously installed Fabric version and its libraries.
        lib.install.install_minecraft_version(fabric_id, str(game), callback=cb)
    if not fabric_profile.is_file():
        raise InstallError("Fabric installation did not create the expected game profile")
    status("Minecraft, Fabric and Java are ready.")
    return fabric_id, java


def build_launch_command(game: Path, catalog: dict, session: dict,
                         address: str = "", ram_gb: int = 4) -> list[str]:
    import minecraft_launcher_lib as lib
    if not all(session.get(x) for x in ("name", "id", "access_token")):
        raise InstallError("A valid Minecraft Microsoft session is required")
    if not 2 <= ram_gb <= 12:
        raise ValueError("Memory selection outside supported range")
    java = _vanilla_runtime(game, catalog["minecraft_version"], lib, {})
    # Avoid leaving an extra Java console on Windows if javaw.exe is present.
    java_w = Path(java).with_name("javaw.exe")
    if java_w.is_file():
        java = str(java_w)
    options = {
        "username": session["name"],
        "uuid": session["id"],
        "token": session["access_token"],
        "launcherName": "UnsupervisedAdultsMC",
        "launcherVersion": "0.2",
        "gameDirectory": str(game),
        "executablePath": str(java),
        "jvmArguments": [f"-Xmx{ram_gb}G", "-Xms1G"],
        **server_options(address),
    }
    return lib.command.get_minecraft_command(profile_id(catalog), str(game), options)


def start_game(game: Path, catalog: dict, session: dict, address: str, logs_dir: Path, ram_gb: int = 4):
    command = build_launch_command(game, catalog, session, address, ram_gb)
    logs_dir.mkdir(parents=True, exist_ok=True)
    # stdout is Minecraft output only; NEVER log the launch command, which includes an access token.
    output = (logs_dir / "latest-game.log").open("w", encoding="utf-8")
    try:
        child = subprocess.Popen(command, cwd=game, stdout=output, stderr=subprocess.STDOUT)
    finally:
        output.close()
    return child
