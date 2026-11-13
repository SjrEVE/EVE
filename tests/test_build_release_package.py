"""Release package includes its tests and excludes machine-private profile data."""
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = "[PASS]"
failures = []


def check(name, condition):
    if condition:
        print(f"{P} {name}")
    else:
        print(f"[FAIL] {name}")
        failures.append(name)


spec = importlib.util.spec_from_file_location("fila_build_release_under_test",
                                               ROOT / "tools" / "build_release.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load build_release.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
old_root, old_read_version, old_argv = (getattr(builder, "ROOT"),
                                         getattr(builder, "read_version"), sys.argv)
try:
    with tempfile.TemporaryDirectory(prefix="fila-release-test-") as tmp:
        repo = Path(tmp)
        for name in ("src/fila_bot", "tools", "config", "tests",
                     "vendor/eve-memory-reader/x64/Release"):
            (repo / name).mkdir(parents=True, exist_ok=True)
        (repo / "src/fila_bot/__init__.py").write_text("", encoding="utf-8")
        (repo / "tools/helper.py").write_text("", encoding="utf-8")
        (repo / "config/security-profile.example.json").write_text(
            json.dumps({"client_sha256": None}), encoding="utf-8")
        (repo / "config/security-profile.kompi.json").write_text(
            json.dumps({"client_sha256": "private-profile-sentinel"}), encoding="utf-8")
        (repo / "tests/run_all.py").write_text("print('[PASS] package test runner')\n", encoding="utf-8")
        (repo / "tests/test_probe.py").write_text("print('[PASS] package fixture test')\n", encoding="utf-8")
        (repo / "LAUNCHER.bat").write_bytes(b"@echo off\nset /p opt=Menu: \n")
        (repo / "CHAY_COURIER_TEST.bat").write_bytes(b"@echo off\n")
        (repo / "CHAY_COURIER_THAT.bat").write_bytes(b"@echo off\n")
        (repo / "vendor/eve-memory-reader/x64/Release/eve-memory-reader.dll").write_bytes(b"test-dll")

        setattr(builder, "ROOT", repo)
        setattr(builder, "read_version", lambda: "1.2.3")
        sys.argv = ["build_release.py", "--skip-tests"]
        rc = builder.main()

        package = repo / "dist/fila-bot-v1.2.3"
        archive_path = repo / "dist/fila-bot-v1.2.3.zip"
        expected_files = ["tests/run_all.py", "tests/test_probe.py",
                          "config/security-profile.example.json"]
        check("builder succeeds on isolated fixture repo", rc == 0)
        check("package contains its test runner and test scripts",
              all((package / p).is_file() for p in expected_files[:2]))
        check("package contains only the safe example profile",
              (package / expected_files[2]).is_file()
              and not (package / "config/security-profile.kompi.json").exists())
        check("Abyss-only package hides legacy courier launchers",
              not (package / "CHAY_COURIER_TEST.bat").exists()
              and not (package / "CHAY_COURIER_THAT.bat").exists())
        launcher_bytes = (package / "LAUNCHER.bat").read_bytes()
        check("packaged Windows launcher uses CRLF line endings",
              launcher_bytes.count(b"\n") == launcher_bytes.count(b"\r\n")
              and launcher_bytes.count(b"\r\n") == 2)
        if archive_path.is_file():
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            archive_ok = (
                "fila-bot-v1.2.3/tests/run_all.py" in names
                and "fila-bot-v1.2.3/tests/test_probe.py" in names
                and "fila-bot-v1.2.3/config/security-profile.kompi.json" not in names
                and "fila-bot-v1.2.3/CHAY_COURIER_TEST.bat" not in names
                and "fila-bot-v1.2.3/CHAY_COURIER_THAT.bat" not in names
            )
        else:
            archive_ok = False
        check("archive contains package tests and excludes the private profile", archive_ok)
        if package.joinpath("MANIFEST.json").is_file():
            manifest = json.loads(package.joinpath("MANIFEST.json").read_text(encoding="utf-8"))
            check("manifest does not fingerprint the local private profile",
                  manifest.get("client_expected_sha256") is None)
        else:
            check("manifest does not fingerprint the local private profile", False)
finally:
    setattr(builder, "ROOT", old_root)
    setattr(builder, "read_version", old_read_version)
    sys.argv = old_argv

if failures:
    raise SystemExit(1)
print(f"{P} release package privacy and test contract")
