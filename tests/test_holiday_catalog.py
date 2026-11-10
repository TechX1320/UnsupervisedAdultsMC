"""Christmas selection for the Fabric 1.21.1 SMP."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
CORE={
    'macaws-holidays', 'snowy-spirit', 'winterly', 'festivities',
    'gingerbread-houses', 'big-gift-snowglobe',
}
OPTIONAL={
    'rainbow-christmas', 'decorationx-christmas', 'seasonal-additions',
    'seasons-greetings',
}

class HolidayCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'pack/catalog.json').read_text(encoding='utf-8'))
        self.by_slug={m.get('slug'):m for m in self.catalog['mods'] if m.get('slug')}

    def test_six_holiday_core_mods_enabled_on_client_and_server(self):
        self.assertEqual(self.catalog['pack_version'],'0.6.0-alpha')
        for slug in CORE:
            with self.subTest(slug=slug):
                entry=self.by_slug[slug]
                self.assertEqual(entry['side'],'both')
                self.assertEqual(entry['type'],'mod')
                self.assertEqual(entry['group'],'holiday')
                self.assertIsNot(entry.get('enabled'),False)

    def test_optional_new_or_overlapping_holiday_mods_disabled(self):
        for slug in OPTIONAL:
            with self.subTest(slug=slug):
                entry=self.by_slug[slug]
                self.assertEqual(entry['side'],'both')
                self.assertFalse(entry['enabled'])

    def test_existing_dependencies_and_game_versions_preserved(self):
        self.assertEqual(self.catalog['minecraft_version'],'1.21.1')
        self.assertEqual(self.catalog['fabric_loader_version'],'0.19.5')
        for slug in ('fabric-api','moonlight','distanthorizons'):
            with self.subTest(slug=slug):
                self.assertIsNot(self.by_slug[slug].get('enabled'),False)
                self.assertEqual(self.by_slug[slug]['side'],'both')

    def test_no_duplicate_modrinth_projects_or_names(self):
        names=[m['name'] for m in self.catalog['mods']]
        slugs=[m['slug'] for m in self.catalog['mods'] if m.get('slug')]
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(len(slugs),len(set(slugs)))

if __name__=='__main__': unittest.main()
