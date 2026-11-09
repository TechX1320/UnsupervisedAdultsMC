"""Owner-only: pin compatible Modrinth files, then commit pack/pack-lock.json."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ua_core as core


def main():
    catalog = json.loads((ROOT / "pack" / "catalog.json").read_text(encoding="utf-8"))
    print(f"Resolving {catalog['name']} for Minecraft {catalog['minecraft_version']} Fabric...")
    lock = core.resolve_catalog(catalog)
    core.validate_lock(lock, catalog)
    lockfile = ROOT / "pack" / "pack-lock.json"
    lockfile.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    warnings = core.manual_warnings(lock)
    report = ROOT / "pack" / "resolution-report.txt"
    report.write_text("\n".join(f"{m['name']}: {m.get('reason','')}\n{m.get('page','')}" for m in warnings) + "\n", encoding="utf-8")
    print(f"\nPinned {len(lock['files'])} files. {len(warnings)} manual/unavailable mods.")
    print(f"Saved: {lockfile}")
    print(f"Report: {report}")
    if core.unresolved_required(lock):
        print("ERROR: Required mods unavailable: " + ", ".join(core.unresolved_required(lock)))
        print("Adjust pack/catalog.json before distributing this lock.")
        raise SystemExit(1)
    print("Commit pack/pack-lock.json and catalog.json to main. Friends update on their next Play click.")


if __name__ == "__main__":
    main()
