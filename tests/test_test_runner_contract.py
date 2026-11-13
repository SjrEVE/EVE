"""Script runner regression. The temporary scripts are synthetic, not game fixtures."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tests" / "run_all.py"
with tempfile.TemporaryDirectory(prefix="fila-suite-") as tmp:
    base = Path(tmp)
    (base / "tests").mkdir()
    (base / "tests" / "test_empty.py").write_text("def test_never_called():\n    assert False\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER)], cwd=base, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=10)
    assert r.returncode != 0, f"zero executed assertions was reported successful: {r.stdout}"
    print("[PASS] zero-pass script fails the suite")

# Synthetic scripts deliberately violate the script-runner contract.
with tempfile.TemporaryDirectory(prefix="fila-suite-") as tmp:
    base = Path(tmp)
    (base / 'tests').mkdir()
    p = base / 'tests' / 'test_script.py'
    p.write_text("print('[PASS] one check')\nprint('[FAIL] failed check')\n", encoding='utf-8')
    r = subprocess.run([sys.executable, str(RUNNER)], cwd=base, capture_output=True, text=True, timeout=10)
    assert r.returncode != 0, 'FAIL marker with exit 0 must fail suite'
    print('[PASS] failure marker cannot hide behind exit zero')
    p.write_text("import time\ntime.sleep(3)\nprint('[PASS] too late')\n", encoding='utf-8')
    env = {**os.environ, 'FILA_TEST_TIMEOUT': '0.2'}
    r = subprocess.run([sys.executable, str(RUNNER)], cwd=base, capture_output=True, text=True, env=env, timeout=8)
    assert r.returncode != 0 and 'TIMEOUT' in r.stdout, r.stdout
    print('[PASS] stalled test times out and fails')
    p.write_text("assert True\nprint('  [PASS] indented check')\nprint('[PASS] second check')\n", encoding='utf-8')
    r = subprocess.run([sys.executable, str(RUNNER)], cwd=base, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0 and '(2 pass)' in r.stdout, r.stdout
    print("[PASS] indented PASS markers count without counting embedded diagnostics")

with tempfile.TemporaryDirectory(prefix="fila-suite-") as tmp:
    base = Path(tmp)
    (base / "tests").mkdir()
    (base / "tests" / "test_local_evidence.py").write_text(
        "print('[SKIP] local-only evidence dump is not shipped')" + chr(10), encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER)], cwd=base, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=10)
    assert r.returncode == 0 and "1 SKIP" in r.stdout and "0 FAIL" in r.stdout, r.stdout
    print("[PASS] explicit local-evidence skip is counted, not reported as a pass")
