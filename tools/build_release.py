"""fila-bot release builder — đóng gói bản có version, gate test trước.

Usage: python tools/build_release.py [--skip-tests] [--label LABEL]
Output: dist/fila-bot-vX.Y.Z/  +  dist/fila-bot-vX.Y.Z.zip

Gate (không bỏ qua trừ --skip-tests, và khi bỏ phải ghi vào CHANGELOG):
  1. VERSION file khớp semver.
  2. tests/run_all.py exit 0, 0 FAIL.
  3. Không chạy trên worktree có file src/tests sửa chưa commit trừ khi --label dirty
     (bản dirty gắn nhãn "-dirty" trong BUILD_INFO để khỏi nhầm bản release).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fila_bot.version import parse, read_version  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=15
                              ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def dirty_paths() -> list[str]:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                             capture_output=True, text=True, timeout=15).stdout
        return [l[3:].strip() for l in out.splitlines()
                if l[3:].strip().startswith(("src/", "tests/", "VERSION", "CHANGELOG"))]
    except Exception:
        return ["<git unavailable>"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--label", default="",
                    help="Nhan build (vd live, rc1). Dan '-dirty' tu dong neu worktree banh.")
    a = ap.parse_args()

    ver = read_version()
    if parse(ver) == (0, 0, 0, None):
        print("[BO CUA] VERSION khong hop le:", ver)
        return 2

    if not a.skip_tests:
        print("[GATE] Chay full suite...")
        r = subprocess.run([sys.executable, "tests/run_all.py"], cwd=ROOT,
                           env={**os.environ, "PYTHONPATH": "src",
                                "PYTHONIOENCODING": "utf-8"})
        if r.returncode != 0:
            print("[BO CUA] Suite FAIL — khong dong goi. Sua test truoc.")
            return 3

    dirty = dirty_paths()
    label = a.label
    if dirty:
        label = (label + "-" if label else "") + "dirty"
        print(f"[CANH BAO] {len(dirty)} file src/tests chua commit -> nhan '{label}'")
        print("           Ban nay KHONG tai lap duoc. Commit roi build lai de ra ban sach.")

    commit = git_commit()
    built = datetime.datetime.now().isoformat(timespec="seconds")
    (ROOT / "BUILD_INFO.json").write_text(json.dumps({
        "version": ver, "commit": commit, "label": label, "built_at": built,
        "dirty_files": dirty[:20],
    }, indent=2), encoding="utf-8")

    dst = ROOT / f"dist/fila-bot-v{ver}"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for name in ("src", "tools", "config"):
        shutil.copytree(ROOT / name, dst / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("VERSION", "CHANGELOG.md", "BUILD_INFO.json", "README.md",
                 "LAUNCHER.bat", "AUTO.bat", "START_UI.bat", "XEM_LOG.bat",
                 "KIEM_TRA_TRANG_THAI.bat", "CHAY_COURIER_TEST.bat",
                 "CHAY_COURIER_THAT.bat", "MO_UI_INSPECTOR.bat"):
        p = ROOT / name
        if p.is_file():
            shutil.copy2(p, dst / name)
    vendor_dll = ROOT / "vendor/eve-memory-reader/x64/Release/eve-memory-reader.dll"
    if vendor_dll.is_file():
        (dst / "src" / "eve-memory-reader.dll").write_bytes(vendor_dll.read_bytes())

    # DLL cạnh src (Eye tìm vendor path trước; copy cả 2 cho chắc)
    vend_dst = dst / "vendor/eve-memory-reader/x64/Release"
    vend_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(vendor_dll, vend_dst / "eve-memory-reader.dll")

    manifest = {
        "version": ver, "commit": commit, "label": label, "built_at": built,
        "python_source_sha256": {str(p.relative_to(dst)).replace("\\", "/"): sha256(p)
                                 for p in sorted((dst / "src").rglob("*.py"))},
        "dll_sha256": sha256(vend_dst / "eve-memory-reader.dll"),
        "client_expected_sha256": json.loads(
            (ROOT / "config/security-profile.kompi.json").read_text(encoding="utf-8-sig")
        ).get("client_sha256"),
    }
    (dst / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zout = dst.with_suffix("")  # placeholder name sans dir
    zip_base = dst.parent / f"fila-bot-v{ver}"
    shutil.make_archive(str(zip_base), "zip", root_dir=dst.parent, base_dir=dst.name)

    print(f"[OK] dist/fila-bot-v{ver}/  +  {zip_base}.zip")
    print(f"     version={ver} commit={commit[:12]} label={label or '(release)'}")
    print(f"     DLL sha256={manifest['dll_sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
