import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import ua_core as core
from tools import export_server
from tools import merge_resourcepacks as merge


class ServerExportTests(unittest.TestCase):
    def make_project(self, root):
        root = Path(root)
        (root / 'pack').mkdir()
        (root / 'Server Setup' / 'mods').mkdir(parents=True)
        catalog = {'schema': 1, 'pack_version': 'test', 'minecraft_version': '1.21.1',
                   'fabric_loader_version': '0.19.5', 'mods': []}
        shared = b'shared-jar'
        server = b'server-jar'
        items = [
            {'name': 'Common', 'path': 'mods/common.jar', 'side': 'both', 'version': '1',
             'url': 'https://cdn.modrinth.com/data/common', 'hashes': {'sha256': hashlib.sha256(shared).hexdigest()}, 'required': True},
            {'name': 'YUNG', 'path': 'mods/server.jar', 'side': 'server', 'version': '1',
             'url': 'https://cdn.modrinth.com/data/server', 'hashes': {'sha256': hashlib.sha256(server).hexdigest()}, 'required': True},
            {'name': 'Client UI', 'path': 'mods/visual.jar', 'side': 'client', 'version': '1',
             'url': 'https://cdn.modrinth.com/data/visual', 'hashes': {'sha256': 'a'*64}, 'required': True},
        ]
        lock = {'schema': 1, 'pack_version': 'test', 'minecraft_version': '1.21.1',
                'fabric_loader_version': '0.19.5', 'catalog_sha256': core.canonical_sha(catalog),
                'files': items, 'skipped': []}
        (root / 'pack' / 'catalog.json').write_text(json.dumps(catalog))
        (root / 'pack' / 'pack-lock.json').write_text(json.dumps(lock))
        return {"common.jar": shared, "server.jar": server}

    def test_exports_jars_only_for_server_and_shared(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            blobs = self.make_project(root)
            def downloader(url, dest, hashes):
                name = Path(dest).name
                Path(dest).write_bytes(blobs[name])
            archive = export_server.export_server(root, status=lambda *_: None, fetch=downloader)
            self.assertTrue((root / 'Server Setup' / 'mods' / 'common.jar').is_file())
            self.assertTrue((root / 'Server Setup' / 'mods' / 'server.jar').is_file())
            self.assertFalse((root / 'Server Setup' / 'mods' / 'visual.jar').exists())
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(sorted(x for x in z.namelist() if x.endswith('.jar')),
                                 ['mods/common.jar', 'mods/server.jar'])
            with mock.patch.object(export_server.core, 'matches', wraps=core.matches) as matches:
                export_server.export_server(root, status=lambda *_: None, fetch=lambda *args: self.fail('no downloads for verified files'))
                self.assertTrue(matches.called)

    def test_required_download_failure_preserves_old_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_project(root)
            existing = root / 'Server Setup' / 'mods' / 'old.jar'
            existing.write_bytes(b'keep-me')
            with self.assertRaises(RuntimeError):
                export_server.export_server(root, status=lambda *_: None,
                                            fetch=lambda *args: (_ for _ in ()).throw(OSError('offline')))
            self.assertEqual(existing.read_bytes(), b'keep-me')
            self.assertFalse((root / 'Server Setup' / 'mods' / 'common.jar').exists())


class ResourcePackMergeTests(unittest.TestCase):
    def pack(self, path, files, fmt=34):
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': fmt, 'description': 'test'}}))
            for name, content in files.items():
                z.writestr(name, content)

    def test_merge_and_conflict_report(self):
        with tempfile.TemporaryDirectory() as td:
            inp, out = Path(td) / 'in', Path(td) / 'out'
            inp.mkdir()
            self.pack(inp / '10-first.zip', {'assets/minecraft/textures/foo.png': b'old', 'data/x/ignored.json': b'data'})
            self.pack(inp / '20-last.zip', {'assets/minecraft/textures/foo.png': b'new', 'assets/minecraft/textures/bar.png': b'bar'})
            result = merge.merge(inp, out, status=lambda *_: None)
            with zipfile.ZipFile(result) as z:
                self.assertEqual(z.read('assets/minecraft/textures/foo.png'), b'new')
                self.assertEqual(z.read('assets/minecraft/textures/bar.png'), b'bar')
                self.assertNotIn('data/x/ignored.json', z.namelist())
                meta = json.loads(z.read('pack.mcmeta'))
                self.assertEqual(meta['pack']['pack_format'], 34)
            self.assertIn('20-last.zip', (out / 'merge-report.txt').read_text())
            sha = hashlib.sha1(result.read_bytes()).hexdigest()
            self.assertIn('resource-pack-sha1=' + sha, (out / 'resource-pack.properties').read_text())

    def test_incompatible_format_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            inp, out = Path(td) / 'in', Path(td) / 'out'
            inp.mkdir()
            self.pack(inp / 'bad.zip', {'assets/foo': b'x'}, fmt=46)
            with self.assertRaises(merge.MergeError):
                merge.merge(inp, out, status=lambda *_: None)
            self.assertFalse((out / merge.PACK_NAME).exists())

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            inp, out = Path(td) / 'in', Path(td) / 'out'
            inp.mkdir()
            self.pack(inp / 'bad.zip', {'../evil.txt': b'x', 'assets/okay': b'y'})
            with self.assertRaises(merge.MergeError):
                merge.merge(inp, out, status=lambda *_: None)

    def test_no_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(merge.MergeError):
                merge.merge(Path(td) / 'not-created', Path(td) / 'out', status=lambda *_: None)


class SharedDependencyTests(unittest.TestCase):
    def test_shared_dependency_is_not_left_client_only(self):
        # Models a mod library first requested by client-only mod, then by
        # a shared mod. Previously that left the library missing from Crafty.
        catalog = {'schema': 1, 'pack_version': 'dep-test',
                   'minecraft_version': '1.21.1', 'fabric_loader_version': '0.19.5',
                   'mods': [
                       {'name': 'ClientFX', 'slug': 'clientfx', 'type': 'mod', 'side': 'client'},
                       {'name': 'Gameplay', 'slug': 'gameplay', 'type': 'mod', 'side': 'both', 'required': True},
                   ]}
        def api(url):
            ident = url.split('/project/')[1].split('/')[0] if '/project/' in url else url.rsplit('/',1)[-1]
            pid = {'clientfx': 'client', 'gameplay': 'gameplay', 'dep-project': 'shared'}[ident]
            deps = [{'dependency_type': 'required', 'project_id': 'dep-project'}] if pid != 'shared' else []
            return [{
                'id': ident + '-v', 'project_id': pid, 'version_number': '1.0',
                'version_type': 'release', 'game_versions': ['1.21.1'],
                'loaders': ['fabric'], 'date_published': '2026-01-01',
                'dependencies': deps,
                'files': [{'filename': pid + '.jar', 'url': 'https://cdn.modrinth.com/data/' + pid + '.jar',
                           'hashes': {'sha256': 'a'*64}, 'primary': True}]
            }]
        lock = core.resolve_catalog(catalog, status=lambda *_: None, api=api)
        dep = next(x for x in lock['files'] if x.get('project_id') == 'shared')
        self.assertEqual(dep['side'], 'both')
        self.assertTrue(dep['required'])

if __name__ == '__main__':
    unittest.main()

