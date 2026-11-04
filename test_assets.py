"""Guard shipped assets and the privacy defaults of each release."""
import json
from pathlib import Path
import unittest
import subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parent


class AssetTests(unittest.TestCase):
    def test_runtime_assets_are_complete(self):
        manifest=json.loads((ROOT/'assets/animations-smooth.json').read_text())
        self.assertEqual(set(manifest),{'idle','rice','wink','smile','wave','happy'})
        assets=(ROOT/'assets').resolve()
        for name,item in manifest.items():
            self.assertEqual(item['fps'],60)
            self.assertGreater(len(item['frames']),20)
            for path in item['frames']:
                file=(assets/path).resolve()
                self.assertTrue(file.is_relative_to(assets))
                with Image.open(file) as im:
                    self.assertEqual(im.size,(256,256))
                    self.assertEqual(im.mode,'RGBA')
    def test_blink_matches_idle_timeline(self):
        idle=json.loads((ROOT/'assets/animations-smooth.json').read_text())['idle']['frames']
        blink=json.loads((ROOT/'assets/blink.json').read_text())['frames']
        self.assertEqual(len(idle),len(blink))
        for path in blink:self.assertTrue((ROOT/'assets'/path).is_file())
    def test_shared_settings_are_anonymous(self):
        settings=json.loads((ROOT/'settings.example.json').read_text())
        self.assertIsNone(settings['thread_id'])
        self.assertFalse(settings['codex_sync'])
        if (ROOT/'.git').exists():
            tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
            self.assertNotIn('settings.json',tracked)
            self.assertNotIn('auth.json',tracked)


if __name__=='__main__':unittest.main()
