"""Version contract tests — file test script theo khung run_all (khong pytest).
Copy khung ok()/PASS tu tests/test_mission.py.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.version import banner, parse, read_version, version_tuple  # noqa: E402

P = "[PASS]"


def ok(name, cond):
    if not cond:
        print(f"[FAIL] {name}")
        raise SystemExit(1)
    print(f"{P} {name}")


# 1. VERSION file par được, khớp semver
v = read_version()
ok(f"VERSION doc duoc va semver: {v}", parse(v) != (0, 0, 0, None))
ok("version_tuple khop", version_tuple()[:3] == parse(v)[:3])

# 2. env override
os.environ["FILA_BOT_VERSION"] = "9.9.9-test"
ok("env FILA_BOT_VERSION ghi de", read_version() == "9.9.9-test")
os.environ.pop("FILA_BOT_VERSION")
ok("tra lai VERSION file sau khi bo env", read_version() == v)

# 3. banner co version + commit
b = banner()
ok(f"banner chua v{v}: {b}", f"v{v}" in b and "FILA-BOT" in b)

# 4. CLI --version
r = subprocess.run([sys.executable, "-m", "fila_bot.cli", "--version"],
                   capture_output=True, text=True, cwd=ROOT,
                   env={**os.environ, "PYTHONPATH": "src"})
ok(f"cli --version exit 0, chua '{v}' ({r.stdout.strip()})",
   r.returncode == 0 and v in r.stdout)

# 5. GUI smoke title co version (headless smoke khong mo cua so)
r2 = subprocess.run([sys.executable, "-m", "fila_bot.ui", "--smoke", "2"],
                    capture_output=True, text=True, cwd=ROOT, timeout=60,
                    env={**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf-8"})
ok("ui --smoke exit 0", r2.returncode == 0)

# 6. CHANGELOG muc moi nhat khop VERSION
ch = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
ok(f"CHANGELOG co muc [{v}]", f"[{v}]" in ch)

# 7. build_info an toan khi khong co BUILD_INFO.json
from fila_bot.version import build_info  # noqa: E402
info = build_info()
ok("build_info tra dict day du",
   set(info) >= {"commit", "label", "built_at"})

print(f"[PASS] version contract: {v} OK")
