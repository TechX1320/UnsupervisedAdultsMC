"""Prepare server-only/both-side mod jars for uploading through Crafty.

Does not modify the user's Debian server, stop the game, or touch world files.
"""
from pathlib import Path
import json
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ua_core as core


def main():
    catalog = json.loads((ROOT / "pack" / "catalog.json").read_text(encoding="utf-8"))
    lockfile = ROOT / "pack" / "pack-lock.json"
    if not lockfile.exists():
        raise SystemExit("Run update_pack.cmd first. A pinned pack-lock.json is required.")
    lock = json.loads(lockfile.read_text(encoding="utf-8"))
    core.validate_lock(lock, catalog)
    if core.unresolved_required(lock, side="server"):
        raise SystemExit("Required server mods unavailable. Fix catalog first.")
    entries = [f for f in lock["files"] if f.get("side") in ("server", "both") and f["path"].startswith("mods/")]
    target = ROOT / ("UnsupervisedAdultsMC-server-" + lock["pack_version"] + ".zip")
    with tempfile.TemporaryDirectory() as d:
        stage = Path(d)
        for index, item in enumerate(entries, 1):
            print(f"[{index}/{len(entries)}] {item['name']}")
            dest = stage / item["path"]
            core.download_verified(item["url"], dest, item["hashes"])
        skipped = [x for x in lock.get("skipped", []) if x.get("side") in ("both", "server")]
        report = "\n".join(x["name"] + " - " + x.get("reason", "") + "\n" + x.get("page", "") for x in skipped)
        (stage / "SERVER_README.txt").write_text(
            "Unsupervised Adults SMP - Fabric 1.21.1 mods\n"
            "Install Fabric server under Crafty separately. Upload the contents of the mods/ folder into the server's mods/ folder.\n"
            "Keep online-mode=true, white-list=true, enforce-whitelist=true. Backup before updates.\n"
            "Server-only or shared mods are included; no client shaders/visual mods.\n\n"
            "Not automatically included:\n" + report + "\n", encoding="utf-8")
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for file in stage.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(stage).as_posix())
    print("Created " + str(target))


if __name__ == "__main__":
    main()
