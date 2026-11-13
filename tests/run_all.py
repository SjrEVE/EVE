"""Run all standalone test scripts; report PASS, explicit local-only SKIP, and FAIL.
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
    total_skipped = 0
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
            skipped = sum(line.lstrip().startswith("[SKIP] ") for line in res.stdout.splitlines())
            if cnt == 0 and skipped == 0:
                failed.append((f, "ZERO_PASS: script executed no reported checks"))
                continue
            total_pass += cnt
            total_skipped += skipped
            if cnt:
                suffix = f", {skipped} skip" if skipped else ""
                print(f"[OK] {f} ({cnt} pass{suffix})")
            else:
                print(f"[SKIP] {f} ({skipped} skip)")

    duration = time.time() - t0
    print("-" * 50)
    print(f"Ket qua: {len(files)} test files, {total_pass} PASS, "
          f"{total_skipped} SKIP, {len(failed)} FAIL in {duration:.2f}s")
    if failed:
        for f, err in failed:
            print(f"\nFAIL: {f}")
            print(err[-500:])
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
