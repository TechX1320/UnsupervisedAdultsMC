"""Reversibly isolate known conflicting unmanaged client JARs.

The curated SMP pack contains EMI and Distant Horizons. Users may separately
install REI/C2ME or keep obsolete EggMorph JARs. No files are deleted here.
"""
from __future__ import annotations

from pathlib import Path


def quarantine_known_conflicts(game: Path, wanted: list[dict], status=print) -> list[dict]:
    mods = game / "mods"
    if not mods.is_dir() or mods.is_symlink():
        return []

    selected = {Path(x.get("path", "")).name.lower() for x in wanted
                if x.get("path", "").startswith("mods/")}
    has_emi = any(n.startswith("emi-") or n.startswith("emi_") for n in selected)
    has_distant_horizons = any("distanthorizons" in n or "distant-horizons" in n for n in selected)
    has_eggmorph = any(n.startswith("eggmorph-") for n in selected)

    def reason_for(name: str) -> str | None:
        if has_emi and (name.startswith("roughlyenoughitems") or name.startswith("rei-") or name.startswith("rei_")):
            return "REI duplicates the curated EMI recipe/item browser"
        if has_distant_horizons and (name.startswith("c2me-") or name.startswith("c2me_")):
            return "Unmanaged C2ME may interfere with DH LOD generation; isolate for stability testing"
        if has_eggmorph and (name.startswith("eggmorph-") or name.startswith("eggmorph_")):
            return "Duplicate/older EggMorph version: keep only the SHA-pinned version"
        return None

    quarantined: list[dict] = []
    backup = game / "ua-disabled-mods"
    for jar in sorted(mods.iterdir(), key=lambda p: p.name.lower()):
        if jar.is_symlink() or not jar.is_file() or jar.suffix.lower() != ".jar":
            continue
        name = jar.name.lower()
        if name in selected:
            continue
        reason = reason_for(name)
        if not reason:
            continue
        backup.mkdir(parents=True, exist_ok=True)
        dest = backup / jar.name
        index = 2
        while dest.exists():
            dest = backup / f"{jar.stem}-backup-{index}{jar.suffix}"
            index += 1
        jar.replace(dest)
        quarantined.append({"name": jar.name, "backup": str(dest), "reason": reason})
        status(f"Isolated conflicting mod: {jar.name} -> ua-disabled-mods ({reason})")

    if quarantined:
        info = backup / "README.txt"
        with info.open("a", encoding="utf-8") as out:
            out.write("\nUnsupervised SMP Check/Repair isolated these optional unmanaged JARs:\n")
            for rec in quarantined:
                out.write(f"- {rec['name']}: {rec['reason']}\n")
            out.write("Nothing was deleted. To restore a mod, quit Minecraft and move its JAR "
                      "back into the .minecraft/mods folder.\n")
    return quarantined
