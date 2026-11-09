"""Chay toan bo test suite nhanh va an toan (8 giay cho 23 files test).
Usage: python tests/run_all.py
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
        res = subprocess.run(
            [sys.executable, f],
            capture_output=True,
            text=True,
            errors="replace",
            env=env,
        )
        if res.returncode != 0:
            failed.append((f, res.stderr or res.stdout))
        else:
            cnt = res.stdout.count("[PASS]")
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
