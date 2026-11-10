"""Owner CLI: generate the full Crafty-importable server ZIP."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ua_core as core
import ua_server


def main():
    catalog = json.loads((ROOT / "pack" / "catalog.json").read_text(encoding="utf-8"))
    lockpath = ROOT / "pack" / "pack-lock.json"
    if not lockpath.is_file():
        raise SystemExit("No pinned pack-lock.json. Run Server Setup/build_server.cmd first.")
    lock = json.loads(lockpath.read_text(encoding="utf-8"))
    try:
        archive = ua_server.build_server_zip(ROOT, catalog, lock)
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit("Crafty server ZIP build failed: " + str(exc)) from exc
    print("\nReady to upload using Crafty's Upload Zip Archive: " + str(archive))


if __name__ == "__main__":
    main()
