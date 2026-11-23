#!/usr/bin/env python3
"""Post-build sanity checks. Not a browser gameplay integration test."""
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
dist = root / "dist"
checks = ["index.html", "asset-manifest.json", "locales/ko/menu.json", "service-worker.js", "backup-manager.js"]
missing = [s for s in checks if not (dist / s).is_file()]
if missing:
    raise RuntimeError("Missing static build files: " + ", ".join(missing))
html = (dist / "index.html").read_text("utf-8")
assert '<html lang="ko">' in html, "Expected Korean page default"
assert "prLang" in html, "Missing Korean language preference"
assert 'src="./backup-manager.js"' in html, "Backup manager script missing from HTML"
backup_script = (dist / "backup-manager.js").read_text("utf-8")
assert "pokerogue-ko-personal-backup" in backup_script
assert "sessionData" in backup_script and "data_Guest" in backup_script
manifest = json.loads((dist / "asset-manifest.json").read_text("utf-8"))
assert manifest["js"].startswith("./"), "Expected relative entry JS"
assert (dist / manifest["js"]).is_file(), "Entry JS is missing"
env = (root / ".env.development").read_text("utf-8")
assert "VITE_BYPASS_LOGIN=1" in env
assert "VITE_SERVER_URL=https://offline.invalid" in env
print("Build file/translation/offline configuration checks passed")
