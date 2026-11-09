import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ua_core as c
import ua_auth as auth
import ua_minecraft as mc


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

    def test_isolated_game_folder(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            path = c.ensure_instance(base, self.catalog())
            self.assertEqual(path, base / "instance")
            self.assertTrue((path / ".minecraft").is_dir())
            self.assertFalse((base / "prism-data").exists())
            own = path / ".minecraft" / "options.txt"
            own.write_text("custom=true")
            c.ensure_instance(base, self.catalog())
            self.assertEqual(own.read_text(), "custom=true")

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
            with mock.patch.object(c, "download_verified", side_effect=OSError("offline")):
                result = c.install_client(lock, root, status=lambda _: None)
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["failed"]), 1)


class AuthTests(unittest.TestCase):
    def test_client_id_required(self):
        with self.assertRaises(auth.AuthenticationError):
            auth.require_client_id({"microsoft_client_id": ""})
        client_id = "12345678-1234-1234-1234-123456789abc"
        self.assertEqual(auth.require_client_id({"microsoft_client_id": client_id}), client_id)

    def test_login_uses_pkce_loopback_without_password_prompt(self):
        captured = {}
        class MockAccount:
            def get_secure_login_data(self, client_id, redirect):
                captured["redirect"] = redirect
                return f"https://login.example.invalid?state=state123&redirect={redirect}", "state123", "verifier123"
            def complete_login(self, client_id, secret, redirect, code, verifier):
                self_args = (client_id, secret, redirect, code, verifier)
                captured["args"] = self_args
                return {"name":"TestPlayer","id":"000000","refresh_token":"refresh","access_token":"access"}
        mock_lib = SimpleNamespace(microsoft_account=MockAccount())
        def fake_browser(url):
            target = captured["redirect"] + "?state=state123&code=12345"
            threading.Thread(target=lambda: urlopen(target, timeout=3).read(), daemon=True).start()
            return True
        with mock.patch.dict(sys.modules, {"minecraft_launcher_lib": mock_lib}):
            result = auth.microsoft_login("12345678-1234-1234-1234-123456789abc", lambda _: None, 5, fake_browser)
        self.assertEqual(result["name"], "TestPlayer")
        self.assertEqual(captured["args"][1], None)
        self.assertEqual(captured["args"][3:], ("12345", "verifier123"))

    def test_saved_token_is_never_plaintext_on_unix(self):
        if sys.platform == "win32":
            self.skipTest("Windows uses DPAPI; UNIX should fail explicitly")
        with self.assertRaises(OSError):
            auth._windows_dpapi(b"sensitive")


class GameTests(unittest.TestCase):
    def catalog(self):
        return {"minecraft_version": "1.21.1", "fabric_loader_version": "0.16.14"}

    def test_fabric_id(self):
        self.assertEqual(mc.profile_id(self.catalog()), "fabric-loader-0.16.14-1.21.1")

    def test_server_address_parsing(self):
        self.assertEqual(mc.server_options("example.com:25566"), {"server":"example.com", "port":"25566"})
        self.assertEqual(mc.server_options(""), {})
        self.assertEqual(mc.server_options("[::1]:25565"), {"server":"::1", "port":"25565"})
        for bad in ("x:0", "x:65536", "fake/path", "hello world", ":25565", "x:abc"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                mc.server_options(bad)

    def test_fabric_installed_and_java_path_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "game"
            java = root / "java.exe"
            java.write_bytes(b"fake")
            calls = []
            def install_mc(version, directory, callback=None):
                calls.append(("minecraft",version))
                version_path = game / "versions" / version
                version_path.mkdir(parents=True,exist_ok=True)
                (version_path / (version+".json")).write_text(json.dumps({"javaVersion":{"component":"java-runtime-gamma"}}))
            def install_fabric(version, directory, loader_version=None,callback=None,java=None):
                calls.append(("fabric",loader_version,java))
                fid = mc.profile_id(self.catalog())
                version_path = game / "versions" / fid
                version_path.mkdir(parents=True,exist_ok=True)
                (version_path / (fid+".json")).write_text("{}")
            fake = SimpleNamespace(
                install=SimpleNamespace(install_minecraft_version=install_mc),
                fabric=SimpleNamespace(install_fabric=install_fabric),
                runtime=SimpleNamespace(get_executable_path=lambda v,d:str(java)),
            )
            with mock.patch.dict(sys.modules, {"minecraft_launcher_lib": fake}):
                version, chosen = mc.ensure_game(game, self.catalog(),lambda _: None)
            self.assertEqual(version, mc.profile_id(self.catalog()))
            self.assertEqual(chosen, str(java))
            self.assertEqual(calls[-1], ("fabric","0.16.14", str(java)))


if __name__ == "__main__":
    unittest.main()

class PortableInstallTests(unittest.TestCase):
    def test_frozen_exe_stores_near_exe(self):
        with mock.patch.object(c.sys, "frozen", True, create=True), \
             mock.patch.object(c.sys, "executable", r"D:\Games\SMP\UnsupervisedAdultsMC.exe"):
            # On POSIX, Windows paths don't parse as platform paths: test the
            # invariant using a native absolute path.
            with tempfile.TemporaryDirectory() as root:
                with mock.patch.object(c.sys, "executable", str(Path(root) / "UnsupervisedAdultsMC.exe")):
                    self.assertEqual(c.app_root(), Path(root) / "UnsupervisedAdultsMC_Data")

    def test_source_code_stores_alongside_source(self):
        with mock.patch.object(c.sys, "frozen", False, create=True):
            self.assertEqual(c.app_root(), Path(c.__file__).resolve().parent / "UnsupervisedAdultsMC_Data")


class JavaFallbackTests(unittest.TestCase):
    def test_verified_temurin_unpack_stays_local(self):
        import io, zipfile
        import ua_java
        with tempfile.TemporaryDirectory() as root:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("jdk-21-jre/bin/java.exe", b"local portable java")
                z.writestr("jdk-21-jre/bin/javaw.exe", b"local portable javaw")
            contents = buf.getvalue()
            sha = hashlib.sha256(contents).hexdigest()
            api = lambda _: [{"binary": {"package": {
                "link": "https://github.com/adoptium/temurin21-binaries/releases/download/test/jre.zip",
                "checksum": sha}}}]
            def fetch(_url, file, hashes, _status):
                self.assertEqual(hashes["sha256"], sha)
                Path(file).write_bytes(contents)
            result = ua_java.ensure_temurin_java(Path(root), lambda _: None, fetch, api)
            self.assertEqual(Path(result), Path(root)/"runtime"/"ua-temurin21"/"bin"/"java.exe")
            self.assertTrue(Path(result).is_file())
            self.assertFalse((Path(root)/"runtime"/"ua-temurin21-download.zip").exists())
            result2 = ua_java.ensure_temurin_java(Path(root), lambda _: None, fetch, api)
            self.assertEqual(result2, result)

    def test_reject_traversal_in_java_archive(self):
        import zipfile
        import ua_java
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root)/"test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../outside-file", "oops")
                z.writestr("jdk/bin/java.exe", "dummy")
            with self.assertRaises(ua_java.JavaInstallError):
                ua_java._safe_extract(archive, Path(root)/"output")


class DeviceFlowTests(unittest.TestCase):
    def test_device_code_never_asks_for_password_or_client_secret(self):
        responses = []
        calls = []
        def post(url, params):
            calls.append((url, dict(params)))
            if url.endswith("devicecode"):
                return {"verification_uri": "https://www.microsoft.com/link", "user_code": "ABCD-EFGH",
                        "device_code": "opaque-device-code", "expires_in": 900, "interval": 5}
            responses.append("polled")
            return ({"error": "authorization_pending"} if len(responses) == 1 else
                    {"access_token": "ms-access", "refresh_token": "ms-refresh"})
        fake_ms = SimpleNamespace(
            authenticate_with_xbl=lambda token:{"Token": "xbl", "DisplayClaims": {"xui":[{"uhs":"user-hash"}]}},
            authenticate_with_xsts=lambda token: {"Token": "xsts"},
            authenticate_with_minecraft=lambda userhash, token: {"access_token": "mc-access"},
            get_profile=lambda token: {"id": "player-uuid", "name": "Player"},
        )
        shown=[]
        with mock.patch.dict(sys.modules, {"minecraft_launcher_lib": SimpleNamespace(microsoft_account=fake_ms)}):
            session=auth.microsoft_device_login("12345678-1234-1234-1234-123456789abc",
                lambda _:None, lambda uri,code:shown.append((uri,code)), post=post, sleep=lambda seconds:None)
        self.assertEqual(shown, [("https://www.microsoft.com/link", "ABCD-EFGH")])
        self.assertEqual(session["name"], "Player")
        self.assertEqual(session["refresh_token"], "ms-refresh")
        self.assertEqual(session["access_token"], "mc-access")
        self.assertEqual(calls[0][1]["scope"], "XboxLive.signin offline_access")
        self.assertFalse(any("password" in fields or "client_secret" in fields for _url,fields in calls))

    def test_device_code_unsupported_triggers_fallback_exception(self):
        def post(url, fields):
            return {"error": "unauthorized_client"}
        with self.assertRaises(auth.DeviceCodeUnavailable):
            auth.microsoft_device_login("12345678-1234-1234-1234-123456789abc",
                lambda _:None, post=post)

class MojangRuntimeFallbackTests(unittest.TestCase):
    def test_missing_mojang_runtime_uses_local_temurin(self):
        import ua_java
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            meta = game / "versions" / "1.21.1"
            meta.mkdir(parents=True)
            (meta / "1.21.1.json").write_text(json.dumps({"javaVersion": {"component": "java-runtime-delta"}}))
            fake_java = game / "runtime" / "ua-temurin21" / "bin" / "java.exe"
            fake_java.parent.mkdir(parents=True)
            fake_java.write_bytes(b"java")
            fake = SimpleNamespace(runtime=SimpleNamespace(get_executable_path=lambda *args: None))
            with mock.patch.object(ua_java, "ensure_temurin_java", return_value=str(fake_java)) as fallback:
                got = mc._vanilla_runtime(game, "1.21.1", fake, {})
            self.assertEqual(got, str(fake_java))
            fallback.assert_called_once()
