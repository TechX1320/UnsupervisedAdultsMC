import hashlib
import json
import tempfile
from pathlib import Path
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ua_core as c


class ResolverTests(unittest.TestCase):
    def catalog(self):
        return {
            "schema": 1, "pack_version": "test", "minecraft_version": "1.21.1",
            "fabric_loader_version": "0.16.14", "mods": [
                {"name": "Sample", "slug": "sample", "type": "mod", "side": "both", "required": True},
                {"name": "Gone", "slug": "gone", "type": "mod", "side": "client"},
                {"name": "Manual Mod", "source": "manual", "type": "mod", "side": "both", "page": "https://example.com"},
                {"name": "Disabled", "slug": "disabled", "type": "mod", "side": "client", "enabled": False}
            ]
        }

    def api(self, url):
        if "/gone/" in url:
            return []
        if "/sample/" in url:
            return [{
                "id": "v1", "project_id": "proj1", "version_number": "1.2.3", "version_type": "release",
                "game_versions": ["1.21.1"], "loaders": ["fabric"], "date_published": "2026-01-01",
                "dependencies": [],
                "files": [{"filename": "sample.jar", "url": "https://cdn.modrinth.com/data/xxx/sample.jar",
                           "hashes": {"sha256": "a" * 64}, "size": 3, "primary": True}]
            }]
        raise AssertionError(f"Unexpected API call: {url}")

    def test_resolve_and_validate(self):
        cat = self.catalog()
        lock = c.resolve_catalog(cat, lambda _: None, api=self.api)
        c.validate_lock(lock, cat)
        self.assertEqual(len(lock["files"]), 1)
        self.assertEqual(lock["files"][0]["path"], "mods/sample.jar")
        self.assertEqual(len(lock["skipped"]), 3)
        self.assertEqual(c.unresolved_required(lock), [])

    def test_missing_required_fails(self):
        cat = self.catalog()
        cat["mods"][0]["slug"] = "gone"
        lock = c.resolve_catalog(cat, lambda _: None, api=self.api)
        self.assertIn("Sample", c.unresolved_required(lock))

    def test_lock_must_match_catalog(self):
        cat = self.catalog()
        lock = c.resolve_catalog(cat, lambda _: None, api=self.api)
        cat["pack_version"] = "changed"
        with self.assertRaises(ValueError):
            c.validate_lock(lock, cat)

    def test_unsafe_path_is_rejected(self):
        cat = self.catalog()
        lock = c.resolve_catalog(cat, lambda _: None, api=self.api)
        lock["files"][0]["path"] = "mods/../../bad.jar"
        with self.assertRaises(ValueError):
            c.validate_lock(lock, cat)

    def test_native_prism_instance(self):
        with tempfile.TemporaryDirectory() as d:
            path = c.ensure_instance(Path(d), self.catalog())
            self.assertEqual(path.name, c.PACK_ID)
            cfg = (path / "mmc-pack.json").read_text()
            self.assertIn("1.21.1", cfg)
            self.assertIn("net.fabricmc.fabric-loader", cfg)
            # A later updater must never clobber instance settings.
            (path / "instance.cfg").write_text("modified")
            c.ensure_instance(Path(d), self.catalog())
            self.assertEqual((path / "instance.cfg").read_text(), "modified")

    def test_optional_download_can_be_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game = root / ".minecraft"
            game.mkdir()
            payload = b"mod file"
            good = game / "mods" / "sample.jar"
            good.parent.mkdir()
            good.write_bytes(payload)
            lock = {
                "pack_version": "1", "skipped": [],
                "files": [
                    {"name": "Sample", "side": "client", "path": "mods/sample.jar",
                     "hashes": {"sha256": hashlib.sha256(payload).hexdigest()}, "required": True,
                     "url": "https://cdn.modrinth.com/test/sample.jar"},
                    {"name": "Optional", "side": "client", "path": "mods/optional.jar",
                     "hashes": {"sha256": "0"*64}, "required": False,
                     "url": "https://cdn.modrinth.com/test/optional.jar"}
                ]
            }
            # Simulate failure using an invalid local URL path, but no internet is needed.
            import unittest.mock
            with unittest.mock.patch.object(c, "download_verified", side_effect=OSError("offline")):
                result = c.install_client(lock, root, status=lambda _: None)
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["failed"]), 1)

    def test_prism_expected_hash_is_pinned(self):
        self.assertEqual(len(c.PRISM_SHA256), 64)
        self.assertTrue(c.PRISM_URL.startswith("https://github.com/PrismLauncher/PrismLauncher/"))


if __name__ == "__main__":
    unittest.main()
