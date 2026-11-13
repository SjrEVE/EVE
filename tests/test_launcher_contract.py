"""The standard launcher surface is Abyss-only and safe by default."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
launcher = (ROOT / "LAUNCHER.bat").read_text(encoding="utf-8-sig")
launcher_lower = launcher.lower()
menu = launcher.split(":MENU", 1)[1].split(":RUN_ABYSS_SIM", 1)[0].lower()
sim_section = launcher.split(":RUN_ABYSS_SIM", 1)[1].split(":RUN_STATUS", 1)[0].lower()
auto = (ROOT / "AUTO.bat").read_text(encoding="utf-8-sig").lower()
log_viewer = (ROOT / "XEM_LOG.bat").read_text(encoding="utf-8-sig").lower()
legacy_test = (ROOT / "CHAY_COURIER_TEST.bat").read_text(encoding="utf-8-sig").lower()
legacy_live = (ROOT / "CHAY_COURIER_THAT.bat").read_text(encoding="utf-8-sig").lower()
batch_names = ("LAUNCHER.bat", "AUTO.bat", "XEM_LOG.bat",
               "CHAY_COURIER_TEST.bat", "CHAY_COURIER_THAT.bat")
batch_crlf = all(
    (ROOT / name).read_bytes().count(b"\n") == (ROOT / name).read_bytes().count(b"\r\n")
    for name in batch_names
)
checks = {
    "main launcher identifies an Abyss-only workflow": "abyss-only" in menu,
    "main menu has no Security option": "security" not in menu,
    "main menu has no Distribution/Courier option": "distribution" not in menu and "courier" not in menu,
    "main menu routes mission execution only to Abyss SIM": "goto run_abyss_sim" in menu,
    "launcher exits on EOF without reusing the previous choice": (
        launcher_lower.find('set "opt="')
        < launcher_lower.find("set /p opt=")
        < launcher_lower.find("if not defined opt exit /b 0")
    ),
    "Abyss SIM is limited to one run": "--max-runs 1" in sim_section,
    "Abyss SIM cannot send live input": "--live" not in sim_section and "--confirm-input" not in sim_section,
    "AUTO launcher runs Abyss rather than Security": "cli abyss" in auto and "cli security" not in auto,
    "AUTO launcher is hard-capped at one run": "--max-runs 1" in auto and "%runs%" not in auto,
    "AUTO launcher is SIM-only": "--live" not in auto and "--confirm-input" not in auto,
    "AUTO launcher does not expose mission/courier modes": all(x not in auto for x in ("security", "distribution", "courier")),
    "AUTO writes only to the Abyss SIM log": "abyss_sim_latest.log" in auto and "live_latest.log" not in auto,
    "XEM_LOG follows the Abyss SIM log": "abyss_sim_latest.log" in log_viewer and "live_latest.log" not in log_viewer,
    "legacy courier test launcher is inert": "legacy disabled" in legacy_test and "cli distribution" not in legacy_test,
    "legacy courier live launcher is inert": "legacy disabled" in legacy_live and "cli distribution" not in legacy_live,
    "Windows batch sources use CRLF for cmd.exe": batch_crlf,
}
for name, passed in checks.items():
    print(("[PASS] " if passed else "[FAIL] ") + name)
if not all(checks.values()):
    raise SystemExit(1)

