#!/usr/bin/env python3
"""Private Korean PokéRogue modifications for pinned upstream beta 59a3eed0."""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import re
import subprocess

EXPECTED_SHA = "59a3eed012eb6de0a4b264f61b9fa9e38e62db38"
EXPECTED_VERSION = "1.12.2.6"
XP_MULTIPLIER = 5
STARTING_GOLD = 1000 * 111

def one(s: str, old: str, new: str, label: str) -> str:
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {n}; upstream incompatible")
    return s.replace(old, new, 1)

def patch(root: Path, require_sha: bool = False) -> list[str]:
    root = root.resolve()
    required = ("src/overrides.ts", "src/system/game-data.ts", "index.html", ".env.development", "package.json")
    for name in required:
        if not (root/name).is_file():
            raise RuntimeError(f"Missing upstream file: {name}")
    pkg = json.loads((root/"package.json").read_text(encoding="utf-8"))
    if pkg["version"] != EXPECTED_VERSION:
        raise RuntimeError(f"Unexpected upstream version {pkg['version']} != {EXPECTED_VERSION}")
    if require_sha:
        sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if sha != EXPECTED_SHA:
            raise RuntimeError(f"Unreviewed upstream revision {sha} != {EXPECTED_SHA}")
    result = {name:(root/name).read_text(encoding="utf-8") for name in required[:-1]}
    result["src/overrides.ts"] = one(
        result["src/overrides.ts"],
        "const overrides = {} satisfies Partial<InstanceType<OverridesType>>;",
        """const overrides = {
  // Local-only changes. Original online account stays untouched.
  XP_MULTIPLIER_OVERRIDE: 5,
  // Current upstream mode uses absolute amount. Base Classic = 1000.
  STARTING_MONEY_OVERRIDE: 111000,
  // null = natural shiny probability; false would force zero shinies.
  SHINY_OVERRIDE: null,
} satisfies Partial<InstanceType<OverridesType>>;""",
        "override defaults"
    )
    data = result["src/system/game-data.ts"]
    data = one(data,
        "    this.initDexData();\n    this.initStarterData();",
        "    this.initDexData();\n    this.initStarterData();\n    this.applyPersonalUnlocks();",
        "initial save unlock")
    data = one(data,
        "    this.consolidateDexData(this.dexData);\n    this.defaultDexData = null;",
        "    this.consolidateDexData(this.dexData);\n    this.applyPersonalUnlocks();\n    this.defaultDexData = null;",
        "existing local save unlock")
    method = """  /** Unlock all normally selectable starters, legendary and mythical included.
   * Do not unlock shiny variants or bypass the starter cost limit.
   */
  private applyPersonalUnlocks(): void {
    const normalAttr =
      DexAttr.NON_SHINY | DexAttr.MALE | DexAttr.FEMALE | DexAttr.DEFAULT_VARIANT | DexAttr.DEFAULT_FORM;
    for (const speciesId of speciesDataRegistry.getAllStarters()) {
      const entry = this.dexData[speciesId];
      if (entry) {
        entry.seenAttr |= normalAttr;
        entry.caughtAttr |= normalAttr;
        entry.natureAttr |= 1 << (Nature.HARDY + 1);
        for (let i = 0; i < entry.ivs.length; i++) {
          entry.ivs[i] = Math.max(entry.ivs[i], 15);
        }
      }
      const starter = this.starterData[speciesId];
      if (starter) starter.abilityAttr |= AbilityAttr.ABILITY_1;
    }
    this.unlocks[Unlockables.ENDLESS_MODE] = true;
    this.unlocks[Unlockables.SPLICED_ENDLESS_MODE] = true;
    this.unlocks[Unlockables.MINI_BLACK_HOLE] = true;
    this.unlocks[Unlockables.EVIOLITE] = true;
  }

"""
    result["src/system/game-data.ts"] = one(data,
        "  private initStarterData(): void {",
        method + "  private initStarterData(): void {",
        "starter unlocking method")
    html = result["index.html"]
    html = one(html, '<html lang="en">', '<html lang="ko">', "HTML language")
    html = one(html, '<title>PokéRogue</title>', '<title>PokéRogue — 개인용 한국어 개조판</title>', "page title")
    html = one(html, '<meta charset="UTF-8" />',
        """<meta charset="UTF-8" />
  <script>try {
    if (!localStorage.getItem('prLang')) localStorage.setItem('prLang', 'ko');
  } catch (_) { /* local storage unavailable */ }</script>""",
        "Korean first use")
    html = html.replace('<link rel="canonical" href="https://pokerogue.net" />', '')
    html = html.replace('<meta property="og:url" content="https://pokerogue.net" />', '')
    result["index.html"] = html
    env = result[".env.development"]
    if env.splitlines().count("VITE_BYPASS_LOGIN=1") != 1:
        raise RuntimeError("Expected offline login-bypass development mode")
    matches = re.findall(r"^VITE_SERVER_URL=.*$", env, re.M)
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one configured API URL")
    result[".env.development"] = env.replace(matches[0], "VITE_SERVER_URL=https://offline.invalid")
    # Validate all anchor matches before any write.
    assert result["src/overrides.ts"].count("XP_MULTIPLIER_OVERRIDE: 5,") == 1
    assert result["src/overrides.ts"].count("STARTING_MONEY_OVERRIDE: 111000,") == 1
    assert result["src/overrides.ts"].count("SHINY_OVERRIDE: null,") == 1
    assert result["src/system/game-data.ts"].count("this.applyPersonalUnlocks();") == 2
    assert result[".env.development"].count("offline.invalid") == 1
    for name, new_text in result.items():
        p = root / name
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(new_text, encoding="utf-8")
        tmp.replace(p)
    return list(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--require-sha", action="store_true")
    args = parser.parse_args()
    print("Patched:", patch(args.source, require_sha=args.require_sha))
