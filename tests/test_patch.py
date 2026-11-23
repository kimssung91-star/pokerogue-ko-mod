import json
import tempfile
from pathlib import Path
import unittest

from patch_pokerogue import patch, EXPECTED_VERSION

class TestPrivatePatch(unittest.TestCase):
    def make_fixture(self, base: Path) -> None:
        (base / "src/system").mkdir(parents=True)
        (base / "src/field").mkdir(parents=True)
        (base / "src/phases").mkdir(parents=True)
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
        (base / "src/field/pokemon.ts").write_text("""  public getMoveset(ignoreOverride = false): PokemonMove[] {
    // Override moveset based on arrays specified in overrides.ts
    return [];
  }
""")
        (base / "src/phases/move-phase.ts").write_text("""  protected checkPP(): boolean {
    const move = this.move;
    if (move.getMove().pp !== -1 && !isIgnorePP(this.useMode) && move.ppUsed >= move.getMovePp()) {
      return true;
    }
    return false;
  }
  protected usePP(): void {
    move.usePp(ppHolder.value);
    globalScene.eventTarget.dispatchEvent(new MoveUsedEvent(this.pokemon.id, move.getMove(), move.ppUsed));
  }
""")
        (base / "index.html").write_text('<html lang="en"><meta charset="UTF-8" /><title>PokéRogue</title><link rel="canonical" href="https://pokerogue.net" /><meta property="og:url" content="https://pokerogue.net" /><script type="module" src="./src/main.ts"></script>')
        (base / ".env.development").write_text("VITE_BYPASS_LOGIN=1\nVITE_SERVER_URL=http://localhost:8001\n")
        (base / "package.json").write_text(json.dumps({"version": EXPECTED_VERSION}))

    def test_main_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            self.make_fixture(path)
            self.assertEqual(len(patch(path)), 6)
            o = (path / "src/overrides.ts").read_text()
            g = (path / "src/system/game-data.ts").read_text()
            self.assertIn("XP_MULTIPLIER_OVERRIDE: 10,", o)
            self.assertIn("STARTING_MONEY_OVERRIDE: 111000,", o)
            self.assertIn("SHINY_OVERRIDE: null,", o)
            self.assertEqual(g.count("this.applyPersonalUnlocks();"), 2)
            self.assertIn("getAllStarters()", g)
            pokemon = (path / "src/field/pokemon.ts").read_text()
            phase = (path / "src/phases/move-phase.ts").read_text()
            self.assertIn("if (this.isPlayer())", pokemon)
            self.assertIn("move.ppUsed = 0;", pokemon)
            self.assertIn("if (!user.isPlayer())", phase)
            self.assertIn("if (!this.pokemon.isPlayer()", phase)
            self.assertIn("new MoveUsedEvent", phase)
            self.assertIn("DexAttr.NON_SHINY", g)
            self.assertIn('lang="ko"', (path / "index.html").read_text())
            self.assertIn('src="./backup-manager.js"', (path / "index.html").read_text())

    def test_source_change_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.make_fixture(p)
            old = p / "src/overrides.ts"
            old.write_text("const overrides = {other: 42};")
            before = {s:(p / s).read_text() for s in ["src/overrides.ts","src/system/game-data.ts","src/field/pokemon.ts","src/phases/move-phase.ts","index.html"]}
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
