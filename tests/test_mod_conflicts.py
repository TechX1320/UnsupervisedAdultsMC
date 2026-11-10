"""Unit tests for the reversible curated-pack conflict repair."""
import tempfile
from pathlib import Path
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ua_conflicts import quarantine_known_conflicts


class ConflictRepairTests(unittest.TestCase):
    def test_rei_c2me_and_old_eggmorph_are_backed_up_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            mods = game / "mods"
            mods.mkdir()
            for name in ("emi-1.jar", "DistantHorizons-3.3.3.jar", "eggmorph-0.2.0-alpha.4.jar",
                         "RoughlyEnoughItems-16.jar", "c2me-fabric-alpha.jar", "eggmorph-0.2.0-alpha.3.jar",
                         "anotherfurniture.jar"):
                (mods / name).write_bytes(name.encode())
            wanted = [{"path": f"mods/{name}"} for name in (
                "emi-1.jar", "DistantHorizons-3.3.3.jar", "eggmorph-0.2.0-alpha.4.jar")]
            moved = quarantine_known_conflicts(game, wanted, status=lambda _: None)
            self.assertEqual({x["name"] for x in moved},
                             {"RoughlyEnoughItems-16.jar", "c2me-fabric-alpha.jar",
                              "eggmorph-0.2.0-alpha.3.jar"})
            self.assertTrue((mods / "anotherfurniture.jar").exists())
            self.assertTrue((mods / "emi-1.jar").exists())
            self.assertTrue((game / "ua-disabled-mods" / "RoughlyEnoughItems-16.jar").exists())
            self.assertTrue((game / "ua-disabled-mods" / "c2me-fabric-alpha.jar").exists())
            self.assertEqual(quarantine_known_conflicts(game, wanted, status=lambda _: None), [])
            self.assertIn("Nothing was deleted", (game / "ua-disabled-mods" / "README.txt").read_text())

    def test_only_conflicts_with_selected_curated_mods_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            mods = game / "mods"
            mods.mkdir()
            (mods / "RoughlyEnoughItems.jar").write_bytes(b"rei")
            (mods / "c2me-alpha.jar").write_bytes(b"c2me")
            self.assertEqual(quarantine_known_conflicts(game, [], status=lambda _: None), [])
            self.assertTrue((mods / "RoughlyEnoughItems.jar").exists())
            self.assertTrue((mods / "c2me-alpha.jar").exists())

    def test_existing_backups_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            mods = game / "mods"
            mods.mkdir()
            (mods / "RoughlyEnoughItems.jar").write_bytes(b"new")
            backup = game / "ua-disabled-mods"
            backup.mkdir()
            (backup / "RoughlyEnoughItems.jar").write_bytes(b"original")
            moved = quarantine_known_conflicts(game, [{"path": "mods/emi-1.jar"}], status=lambda _: None)
            self.assertEqual(len(moved), 1)
            self.assertEqual((backup / "RoughlyEnoughItems.jar").read_bytes(), b"original")
            self.assertEqual((backup / "RoughlyEnoughItems-backup-2.jar").read_bytes(), b"new")


if __name__ == "__main__":
    unittest.main()
