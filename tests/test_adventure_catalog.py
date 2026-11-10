"""Validate our shipped SMP adventure selection without downloading the mods."""
import json
from pathlib import Path
import unittest
import ua_core as core

ROOT = Path(__file__).resolve().parents[1]

class AdventurePackCatalogTests(unittest.TestCase):
    def get_catalog(self):
        return json.loads((ROOT / 'pack' / 'catalog.json').read_text(encoding='utf-8'))

    def test_loader_and_pack_version(self):
        p = self.get_catalog()
        core.check_catalog(p)
        self.assertEqual(p['minecraft_version'], '1.21.1')
        self.assertEqual(p['fabric_loader_version'], '0.19.5')
        self.assertEqual(p['pack_version'], '0.5.0-alpha')

    def test_no_duplicate_modrinth_projects(self):
        p=self.get_catalog()
        names=[m['name'] for m in p['mods']]
        projects=[m['slug'] for m in p['mods'] if m.get('source','modrinth')=='modrinth']
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(len(projects),len(set(projects)))

    def test_known_server_missing_dependencies_included(self):
        p=self.get_catalog()
        byslug={m.get('slug'):m for m in p['mods'] if m.get('slug')}
        for name in ('fabric-language-kotlin', 'simply-tooltips', 'moogs-structure-lib', 'moonlight'):
            with self.subTest(name=name):
                m=byslug[name]
                self.assertNotEqual(m.get('enabled'),False)
                self.assertIn(m['side'], ('both','server'))
                self.assertTrue(m.get('required',False))

    def test_adventure_server_and_shared_sides(self):
        p=self.get_catalog()
        byslug={m.get('slug'):m for m in p['mods'] if m.get('slug')}
        for slug in ('dungeons-and-taverns','moogs-voyager-structures','mns-moogs-nether-structures',
                     'mes-moogs-end-structures','yungs-better-strongholds','incendium','nullscape',
                     'structory','structory-towers','tidal-towns','chunky'):
            with self.subTest(slug=slug): self.assertEqual(byslug[slug]['side'],'server')
        for slug in ('lootr','farmers-delight-refabricated','supplementaries', 'creeper-overhaul',
                     'mutant-monsters','another-furniture','immersive-aircraft', 'travelersbackpack'):
            with self.subTest(slug=slug): self.assertEqual(byslug[slug]['side'],'both')
        self.assertEqual(byslug['emi']['side'],'client')

    def test_optional_overlap_is_not_automatically_installed(self):
        p=self.get_catalog()
        byslug={m.get('slug'):m for m in p['mods'] if m.get('slug')}
        for slug in ('ct-overhaul-village', 'yungs-better-end-island','lets-do-furniture',
                     'adventurez','deeperdarker','noisium'):
            with self.subTest(slug=slug):self.assertFalse(byslug[slug]['enabled'])

if __name__=='__main__':unittest.main()
