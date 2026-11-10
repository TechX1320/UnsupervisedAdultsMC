"""No-network unit tests for the portable Prism + modpack workflow."""
import hashlib
import io
import json
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ua_core as core
import ua_prism as prism


class PackTests(unittest.TestCase):
    def catalog(self):
        return {
            "schema": 1, "pack_version": "test", "minecraft_version": "1.21.1",
            "fabric_loader_version": "0.19.5", "mods": [
                {"name": "Sample", "slug": "sample", "type": "mod", "side": "both", "required": True},
                {"name": "Gone", "slug": "gone", "type": "mod", "side": "client"},
                {"name": "Manual", "source": "manual", "type": "mod", "side": "both"},
                {"name": "Disabled", "slug": "disabled", "type": "mod", "side": "client", "enabled": False},
            ],
        }

    @staticmethod
    def api(url):
        if "/gone/" in url:
            return []
        if "/sample/" in url:
            return [{
                "id": "v1", "project_id": "sample", "version_number": "1.2.3", "version_type": "release",
                "game_versions": ["1.21.1"], "loaders": ["fabric"], "date_published": "2026-01-01",
                "dependencies": [],
                "files": [{"filename": "sample.jar", "url": "https://cdn.modrinth.com/data/x/sample.jar",
                           "hashes": {"sha256": "a" * 64}, "size": 3, "primary": True}],
            }]
        raise AssertionError("Unexpected Modrinth request: " + url)

    def test_resolve_validate_and_skip(self):
        cat = self.catalog()
        lock = core.resolve_catalog(cat, lambda _: None, api=self.api)
        core.validate_lock(lock, cat)
        self.assertEqual(lock["files"][0]["path"], "mods/sample.jar")
        self.assertEqual(len(lock["skipped"]), 3)
        self.assertEqual(core.unresolved_required(lock), [])

    def test_required_unavailable_blocks_play(self):
        cat = self.catalog()
        cat["mods"][0]["slug"] = "gone"
        lock = core.resolve_catalog(cat, lambda _: None, api=self.api)
        self.assertIn("Sample", core.unresolved_required(lock))

    def test_changed_catalog_invalidates_old_lock(self):
        cat = self.catalog()
        lock = core.resolve_catalog(cat, lambda _: None, api=self.api)
        cat["pack_version"] = "new"
        with self.assertRaises(ValueError):
            core.validate_lock(lock, cat)

    def test_traversal_in_mod_path_is_rejected(self):
        cat = self.catalog()
        lock = core.resolve_catalog(cat, lambda _: None, api=self.api)
        lock["files"][0]["path"] = "mods/../../bad.jar"
        with self.assertRaises(ValueError):
            core.validate_lock(lock, cat)

    def test_optional_download_failure_does_not_break_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp)
            game = instance / ".minecraft"
            game.mkdir()
            payload = b"test"
            good = game / "mods" / "working.jar"
            good.parent.mkdir()
            good.write_bytes(payload)
            lock = {"pack_version": "test", "skipped": [], "files": [
                {"name": "Working", "side": "client", "path": "mods/working.jar",
                 "hashes": {"sha256": hashlib.sha256(payload).hexdigest()}, "required": True,
                 "url": "https://cdn.modrinth.com/working.jar"},
                {"name": "Optional", "side": "client", "path": "mods/missing.jar",
                 "hashes": {"sha256": "0" * 64}, "required": False,
                 "url": "https://cdn.modrinth.com/missing.jar"},
            ]}
            with mock.patch.object(core, "download_verified", side_effect=OSError("offline")):
                result = core.install_client(lock, instance, status=lambda _: None)
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["updated"], 0)
            self.assertEqual(len(result["failed"]), 1)
            self.assertEqual(good.read_bytes(), payload)


class PortablePrismTests(unittest.TestCase):
    def catalog(self):
        return {"schema": 1, "minecraft_version": "1.21.1",
                "fabric_loader_version": "0.19.5", "mods": []}

    def test_portable_root_for_frozen_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "UnsupervisedAdultsMC.exe"
            with mock.patch.object(core.sys, "frozen", True, create=True), \
                 mock.patch.object(core.sys, "executable", str(exe)):
                self.assertEqual(core.app_root(), Path(tmp) / "UnsupervisedAdultsMC_Data")

    def test_source_mode_uses_source_folder(self):
        with mock.patch.object(core.sys, "frozen", False, create=True):
            self.assertEqual(core.app_root(), Path(core.__file__).resolve().parent / "UnsupervisedAdultsMC_Data")

    def test_instance_has_fixed_game_and_fabric_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instance = prism.ensure_instance(root, self.catalog())
            self.assertEqual(instance, root / "prism-data" / "instances" / core.PACK_ID)
            self.assertTrue((instance / ".minecraft").is_dir())
            data = json.loads((instance / "mmc-pack.json").read_text())
            self.assertEqual(data["components"][0]["version"], "1.21.1")
            self.assertEqual(data["components"][1]["uid"], "net.fabricmc.fabric-loader")
            self.assertEqual(data["components"][1]["version"], "0.19.5")
            (instance / "instance.cfg").write_text("user changed")
            prism.ensure_instance(root, self.catalog())
            self.assertEqual((instance / "instance.cfg").read_text(), "user changed")

    def test_existing_prism_instance_upgrades_loader_and_preserves_player_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = dict(self.catalog(), fabric_loader_version="0.19.5")
            instance = prism.ensure_instance(root, old)
            metadata = instance / "mmc-pack.json"
            profile = json.loads(metadata.read_text())
            profile["components"][1]["version"] = "0.16.14"
            profile["components"][1]["userProperty"] = "keep"
            profile["components"].append({"uid": "my.custom.component", "version": "1"})
            profile["notes"] = {"settings": "preserved"}
            metadata.write_text(json.dumps(profile), encoding="utf-8")
            save = instance / ".minecraft" / "saves" / "myworld" / "level.dat"
            save.parent.mkdir(parents=True)
            save.write_bytes(b"my-test-world")
            (instance / "instance.cfg").write_text("my custom settings", encoding="utf-8")
            messages = []
            prism.ensure_instance(root, self.catalog(), messages.append)
            upgraded = json.loads(metadata.read_text())
            loader = next(c for c in upgraded["components"] if c["uid"] == "net.fabricmc.fabric-loader")
            self.assertEqual(loader["version"], "0.19.5")
            self.assertEqual(loader["userProperty"], "keep")
            self.assertIn({"uid": "my.custom.component", "version": "1"}, upgraded["components"])
            self.assertEqual(upgraded["notes"], {"settings": "preserved"})
            self.assertEqual(save.read_bytes(), b"my-test-world")
            self.assertEqual((instance / "instance.cfg").read_text(), "my custom settings")
            self.assertTrue(any("0.16.14 to 0.19.5" in msg for msg in messages))
            # Subsequent launch shouldn't rewrite the file unnecessarily.
            before = metadata.read_bytes()
            messages.clear()
            prism.ensure_instance(root, self.catalog(), messages.append)
            self.assertEqual(metadata.read_bytes(), before)
            self.assertFalse(messages)

    def test_malformed_prism_metadata_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instance = prism.ensure_instance(root, self.catalog())
            meta = instance / "mmc-pack.json"
            meta.write_text("{bad json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Existing Prism instance metadata is invalid"):
                prism.ensure_instance(root, self.catalog())
            self.assertEqual(meta.read_text(), "{bad json")

    def test_older_fabric_loader_is_rejected_in_published_catalog(self):
        old = dict(self.catalog(), fabric_loader_version="0.16.14")
        with self.assertRaisesRegex(ValueError, "0.19.5 or newer"):
            core.check_catalog(old)

    @staticmethod
    def make_archive(members):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            for name, value in members.items():
                z.writestr(name, value)
        return out.getvalue()

    def test_pinned_prism_archive_installs_with_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blob = self.make_archive({"PrismLauncher/prismlauncher.exe": b"mock-exe"})
            calls = []
            def download(url, dest, hashes, status, max_bytes):
                calls.append((url, hashes, max_bytes))
                Path(dest).write_bytes(blob)
            exe = prism.ensure_prism(root, lambda _: None, fetch=download)
            self.assertTrue(exe.is_file())
            self.assertEqual(exe.read_bytes(), b"mock-exe")
            self.assertEqual(calls[0][1], {"sha256": prism.PRISM_SHA256})
            self.assertTrue(calls[0][0].startswith("https://github.com/PrismLauncher/"))
            self.assertEqual(prism.ensure_prism(root, lambda _: None, fetch=download), exe)
            self.assertEqual(len(calls), 1)
            self.assertFalse((root / "prism-download.zip").exists())

    def test_rejects_traversal_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.zip"
            archive.write_bytes(self.make_archive({
                "../outside.txt": b"unsafe", "prism/prismlauncher.exe": b"exe",
            }))
            staging = root / "staging"
            staging.mkdir()
            with self.assertRaises(ValueError):
                prism._unpack_verified(archive, staging)
            self.assertFalse((root / "outside.txt").exists())

    def test_rejects_symlink_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "symlink.zip"
            with zipfile.ZipFile(archive, "w") as z:
                link = zipfile.ZipInfo("prism/linked")
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(link, "../../something")
                z.writestr("prism/prismlauncher.exe", b"exe")
            staging = root / "staging"
            staging.mkdir()
            with self.assertRaises(ValueError):
                prism._unpack_verified(archive, staging)

    def test_first_run_account_indicator_never_reads_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(prism.has_prism_account_file(root))
            path = prism.accounts_file(root)
            path.parent.mkdir(parents=True)
            path.write_bytes(b"private token data")
            self.assertTrue(prism.has_prism_account_file(root))

    def test_cli_uses_private_data_root_and_online_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "prism-bin" / "prismlauncher.exe"
            exe.parent.mkdir()
            exe.write_bytes(b"exe")
            prism.ensure_instance(root, self.catalog())
            calls = []
            def popen(args, cwd):
                calls.append((args, cwd))
                return "proc"
            self.assertEqual(prism.open_prism(root, exe, popen=popen), "proc")
            self.assertEqual(calls[0][0], [str(exe), "-d", str(root / "prism-data")])
            self.assertEqual(prism.launch_instance(root, exe, "smp.example.org:25565", popen=popen), "proc")
            args = calls[1][0]
            self.assertEqual(args[:3], [str(exe), "-d", str(root / "prism-data")])
            self.assertEqual(args[3:], ["--launch", core.PACK_ID, "--server", "smp.example.org:25565"])
            self.assertNotIn("--offline", args)
            self.assertEqual(calls[1][1], exe.parent)

    def test_server_address_validation(self):
        self.assertEqual(prism.validate_server_address("smp.example.com:25565"), "smp.example.com:25565")
        self.assertEqual(prism.validate_server_address("[::1]:25565"), "[::1]:25565")
        self.assertEqual(prism.validate_server_address(""), "")
        for bad in ("smp/path", "server:0", "server:65536", "server:", "server:abc", ":25565", "a b", "::1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                prism.validate_server_address(bad)

    def test_migrates_existing_mods_and_saves_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inst = prism.ensure_instance(root, self.catalog())
            src = root / "instance" / ".minecraft"
            (src / "mods").mkdir(parents=True)
            (src / "mods" / "prior.jar").write_bytes(b"old mod")
            (src / "saves" / "MyWorld").mkdir(parents=True)
            (src / "saves" / "MyWorld" / "level.dat").write_bytes(b"world")
            (src / "libraries").mkdir()
            (src / "libraries" / "old.jar").write_bytes(b"no need")
            dest = inst / ".minecraft"
            (dest / "mods").mkdir()
            (dest / "mods" / "prior.jar").write_bytes(b"newer mod")
            count = prism.migrate_legacy(root, inst, status=lambda _: None)
            self.assertGreater(count, 0)
            self.assertEqual((dest / "mods" / "prior.jar").read_bytes(), b"newer mod")
            self.assertTrue((src / "mods" / "prior.jar").exists())  # collision retained
            self.assertEqual((dest / "saves" / "MyWorld" / "level.dat").read_bytes(), b"world")
            self.assertTrue((src / "libraries" / "old.jar").is_file())
            self.assertEqual(prism.migrate_legacy(root, inst, status=lambda _: None), 0)


if __name__ == "__main__":
    unittest.main()
