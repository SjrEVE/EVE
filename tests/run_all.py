"""Chay toan bo test suite nhanh va an toan (8 giay cho 23 files test).
Usage: python tests/run_all.py
Ket qua cung duoc append ra logs/live_latest.log (UTF-8) cho XEM_LOG.bat.
"""
import glob
import os
import subprocess
import sys
import time


def main():
    t0 = time.time()
    files = sorted(glob.glob("tests/test_*.py"))
    total_pass = 0
    failed = []
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONIOENCODING"] = "utf-8"

    for f in files:
        try:
            res = subprocess.run(
                [sys.executable, f], capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env,
                timeout=float(env.get("FILA_TEST_TIMEOUT", "60")),
            )
        except subprocess.TimeoutExpired:
            failed.append((f, "TIMEOUT: test exceeded per-file budget"))
            continue
        if res.returncode != 0:
            failed.append((f, res.stderr or res.stdout))
        else:
            if any(line.lstrip().startswith("[FAIL]") for line in (res.stdout + res.stderr).splitlines()):
                failed.append((f, "FAIL marker despite exit zero\n" + res.stdout))
                continue
            cnt = sum(line.lstrip().startswith("[PASS] ") for line in res.stdout.splitlines())
            if cnt == 0:
                failed.append((f, "ZERO_PASS: script executed no reported checks"))
                continue
            total_pass += cnt
            print(f"[OK] {f} ({cnt} pass)")

    duration = time.time() - t0
    print("-" * 50)
    print(f"Ket qua: {len(files)} test files, {total_pass} PASS, {len(failed)} FAIL in {duration:.2f}s")
    if failed:
        for f, err in failed:
            print(f"\nFAIL: {f}")
            print(err[-500:])
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
