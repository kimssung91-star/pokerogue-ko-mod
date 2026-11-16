import json
import tempfile
from pathlib import Path
import unittest

from patch_pokerogue import patch, EXPECTED_VERSION

class TestPrivatePatch(unittest.TestCase):
    def make_fixture(self, base: Path) -> None:
        (base / "src/system").mkdir(parents=True)
        (base / "src/overrides.ts").write_text("const overrides = {} satisfies Partial<InstanceType<OverridesType>>;")
        (base / "src/system/game-data.ts").write_text("""  constructor() {
    this.initDexData();
    this.initStarterData();
  }
  private initParsedSystem() {
    this.consolidateDexData(this.dexData);
    this.defaultDexData = null;
  }
  private initStarterData(): void {}
""")
        (base / "index.html").write_text('<html lang="en"><meta charset="UTF-8" /><title>PokéRogue</title><link rel="canonical" href="https://pokerogue.net" /><meta property="og:url" content="https://pokerogue.net" />')
        (base / ".env.development").write_text("VITE_BYPASS_LOGIN=1\nVITE_SERVER_URL=http://localhost:8001\n")
        (base / "package.json").write_text(json.dumps({"version": EXPECTED_VERSION}))

    def test_main_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            self.make_fixture(path)
            self.assertEqual(len(patch(path)), 4)
            o = (path / "src/overrides.ts").read_text()
            g = (path / "src/system/game-data.ts").read_text()
            self.assertIn("XP_MULTIPLIER_OVERRIDE: 5,", o)
            self.assertIn("STARTING_MONEY_OVERRIDE: 111000,", o)
            self.assertIn("SHINY_OVERRIDE: null,", o)
            self.assertEqual(g.count("this.applyPersonalUnlocks();"), 2)
            self.assertIn("getAllStarters()", g)
            self.assertIn("DexAttr.NON_SHINY", g)
            self.assertIn('lang="ko"', (path / "index.html").read_text())

    def test_source_change_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.make_fixture(p)
            old = p / "src/overrides.ts"
            old.write_text("const overrides = {other: 42};")
            before = {s:(p / s).read_text() for s in ["src/overrides.ts","src/system/game-data.ts","index.html"]}
            with self.assertRaises(RuntimeError):
                patch(p)
            self.assertEqual(before, {s:(p / s).read_text() for s in before})

    def test_version_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.make_fixture(p)
            (p / "package.json").write_text(json.dumps({"version": "999.0.0"}))
            with self.assertRaises(RuntimeError):
                patch(p)

if __name__ == "__main__":
    unittest.main()
