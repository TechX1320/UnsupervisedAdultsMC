"""No-network tests for the complete Crafty ZIP importer."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import ua_core as core
import ua_server


class CraftyZipTests(unittest.TestCase):
    @staticmethod
    def setup():
        catalog = {
            "schema": 1,
            "name": "Unsupervised SMP",
            "pack_version": "0.4-test",
            "minecraft_version": "1.21.1",
            "fabric_loader_version": "0.16.14",
            "mods": [],
        }
        files = []
        content = {
            "fabric-api.jar": b"api-jar",
            "structure.jar": b"dungeon-jar",
            "sodium.jar": b"client-only-jar",
        }
        for name, side in (("fabric-api.jar", "both"), ("structure.jar", "server"), ("sodium.jar", "client")):
            files.append({
                "name": name,
                "side": side,
                "required": True,
                "path": "mods/" + name,
                "hashes": {"sha256": hashlib.sha256(content[name]).hexdigest()},
                "url": "https://cdn.modrinth.com/data/test/" + name,
            })
        lock = {
            "schema": 1, "pack_version": "0.4-test", "minecraft_version": "1.21.1",
            "fabric_loader_version": "0.16.14",
            "catalog_sha256": core.canonical_sha(catalog),
            "files": files, "skipped": [],
        }
        return catalog, lock, content

    @staticmethod
    def fake_fabric(url, path):
        assert url == "https://meta.fabricmc.net/v2/versions/loader/1.21.1/0.16.14/1.1.2/server/jar"
        with zipfile.ZipFile(path, "w") as jar:
            jar.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nMain-Class: net.fabricmc.main.Main\n")
            jar.writestr("net/fabricmc/main/Main.class", b"binary-class")

    def test_zip_contains_root_server_launcher_mods_and_whitelist(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            called = []

            def fetch_mod(url, dest, hashes):
                name = url.rsplit("/", 1)[-1]
                called.append(name)
                Path(dest).write_bytes(content[name])

            archive = ua_server.build_server_zip(
                Path(td), cat, lock, status=lambda *_: None,
                fetch_fabric=self.fake_fabric, fetch_mod=fetch_mod)
            self.assertTrue(archive.name.startswith("UnsupervisedSMP-Crafty-"))
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
                self.assertIn("fabric-server-launch.jar", names)
                self.assertIn("mods/fabric-api.jar", names)
                self.assertIn("mods/structure.jar", names)
                self.assertNotIn("mods/sodium.jar", names)
                self.assertIn("server.properties", names)
                self.assertIn("CRAFTY-IMPORT.txt", names)
                self.assertIn("UNAVAILABLE-MODS.txt", names)
                self.assertNotIn("eula.txt", names)
                self.assertNotIn("Files/fabric-server-launch.jar", names)
                self.assertTrue(z.read("fabric-server-launch.jar").startswith(b"PK"))
                properties = z.read("server.properties").decode()
                self.assertIn("online-mode=true", properties)
                self.assertIn("white-list=true", properties)
                self.assertIn("enforce-whitelist=true", properties)
                self.assertIn("level-name=UnsupervisedSMP", properties)
                self.assertIn("fabric-server-launch.jar", z.read("CRAFTY-IMPORT.txt").decode())
            self.assertEqual(sorted(called), ["fabric-api.jar", "structure.jar"])
            # Cached files are not re-downloaded on subsequent exports.
            ua_server.build_server_zip(
                Path(td), cat, lock, status=lambda *_: None,
                fetch_fabric=lambda *args: self.fail("existing fabric jar should be reused"),
                fetch_mod=lambda *args: self.fail("already verified mod should be reused"))

    def test_egg_morph_can_be_owner_provided_locally_without_private_download(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            jar = b"egg-morph-binary"
            lock["files"].append({
                "name": "EggMorph (experimental)", "side": "both", "required": False,
                "path": "mods/eggmorph-0.2.0-alpha.jar",
                "hashes": {"sha256": hashlib.sha256(jar).hexdigest()},
                "url": "https://github.com/private/EggMorph/releases/download/test/eggmorph-0.2.0-alpha.jar",
            })
            cache = Path(td) / "Server Setup" / "mods"
            cache.mkdir(parents=True)
            (cache / "eggmorph-0.2.0-alpha.jar").write_bytes(jar)
            def fetch_mod(url, dest, hashes):
                if "eggmorph" in url:
                    self.fail("Owner-provided hash-matched private JAR should be reused")
                Path(dest).write_bytes(content[url.rsplit("/", 1)[-1]])
            archive = ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                                  fetch_fabric=self.fake_fabric, fetch_mod=fetch_mod)
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(z.read("mods/eggmorph-0.2.0-alpha.jar"), jar)

    def test_required_server_mod_failure_prevents_zip(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            with self.assertRaisesRegex(ua_server.ServerBuildError, "Required server mod"):
                ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                           fetch_fabric=self.fake_fabric,
                                           fetch_mod=lambda *args: (_ for _ in ()).throw(OSError("offline")))
            self.assertFalse(list((Path(td) / "Server Setup").glob("UnsupervisedSMP-Crafty-*.zip")))

    def test_optional_failed_mod_reports_problem_in_zip(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            lock["files"].append({
                "name": "EggMorph (private)", "side": "both", "required": False,
                "path": "mods/eggmorph.jar", "hashes": {"sha256": "f" * 64},
                "url": "https://github.com/private/EggMorph/releases/download/a/eggmorph.jar",
            })
            def fetch_mod(url, dest, hashes):
                if "eggmorph" in url:
                    raise OSError("404: private GitHub release")
                Path(dest).write_bytes(content[url.rsplit("/", 1)[-1]])
            archive = ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                                  fetch_fabric=self.fake_fabric, fetch_mod=fetch_mod)
            with zipfile.ZipFile(archive) as z:
                self.assertNotIn("mods/eggmorph.jar", z.namelist())
                self.assertIn("EggMorph (private)", z.read("UNAVAILABLE-MODS.txt").decode())

    def test_zip_rejects_invalid_lock_or_missing_required(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            lock["files"][0]["path"] = "mods/../../evil.jar"
            with self.assertRaises(ValueError):
                ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                           fetch_fabric=self.fake_fabric)
            cat, lock, content = self.setup()
            lock["skipped"].append({"name": "Missing worldgen", "side": "server", "required": True})
            with self.assertRaisesRegex(ua_server.ServerBuildError, "Missing worldgen"):
                ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                           fetch_fabric=self.fake_fabric)

    def test_bad_server_jar_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as td:
            cat, lock, content = self.setup()
            with self.assertRaisesRegex(ua_server.ServerBuildError, "validate Fabric"):
                ua_server.build_server_zip(Path(td), cat, lock, status=lambda *_: None,
                                           fetch_fabric=lambda url, target: target.write_text("not a JAR"))


if __name__ == "__main__":
    unittest.main()
