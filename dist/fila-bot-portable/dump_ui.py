"""dump_ui.py — dump UI tree THẬT từ EVE client đang chạy (read-only).

Chạy: python dump_ui.py [--out <file.json>]
Output: JSON đầy đủ + bảng tóm tắt node types + các node quan trọng (ShipUI, gauges,
overview, selected item, undock button...).
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fila_bot.eye import Eye  # noqa: E402

DLL = Path(__file__).resolve().parent / "src" / "eve-memory-reader.dll"


def summarize(eye: Eye) -> str:
    root = eye.root
    types: dict[str, int] = {}
    names: dict[str, int] = {}
    for n in Eye.walk(root):
        t = str(n.get("type", "?"))
        types[t] = types.get(t, 0) + 1
        nm = str(n.get("attrs", {}).get("_name", ""))[:60]
        if nm:
            names[nm] = names.get(nm, 0) + 1
    lines = ["=== NODE TYPES ==="]
    for t, c in sorted(types.items(), key=lambda x: -x[1])[:60]:
        lines.append(f"{c:5d}  {t}")
    lines.append("\n=== NODE NAMES (60 đầu) ===")
    for nm, c in sorted(names.items(), key=lambda x: -x[1])[:60]:
        lines.append(f"{c:5d}  {nm}")
    # các node quan trọng
    lines.append("\n=== NODES QUAN TRỌNG ===")
    checks = [
        ("ShipUI", None), ("ShipSlot", None), ("ModuleButton", None),
        ("CapacitorContainer", None), ("OverView", None),
        ("OverviewScrollEntry", None), ("ActiveItem", None),
        ("DroneView", None), ("MessageBox", None), ("KeyActivationWindow", None),
    ]
    for label, _ in checks:
        found = eye.find(type=label, select_many=True)
        extra = ""
        if found:
            xy = Eye.center_xy(found[0])
            extra = f" @ {xy}"
        lines.append(f"{label}: {'KHÔNG THẤY' if not found else f'{len(found)} node{extra}'}")
    # gauge names thật (HUD mới?)
    for g in ("shieldGauge", "armorGauge", "structureGauge", "speedGauge", "SpeedGauge"):
        nodes = eye.find(_name=g, select_many=True)
        lines.append(f"gauge _name={g}: {len(nodes)}")
    # tọa độ undock-ish button
    undocks = eye.find(_setText="Undock", select_many=True)
    lines.append(f"button 'Undock' (_setText): {len(undocks)}"
                 + (f" @ {Eye.center_xy(undocks[0])}" if undocks else ""))
    return "\n".join(lines)


def main() -> int:
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else (
        Path(__file__).resolve().parent / "ui_dump.json")
    print("Đang đọc UI tree từ EVE client (read-only)...")
    eye = Eye(dll_path=str(DLL))
    root = eye.refresh()
    if root is None:
        print("KHÔNG đọc được UI tree — client chưa chạy DLL initialize fail?")
        return 2
    Path(out_path).write_text(json.dumps(root, ensure_ascii=False, indent=1)[:8_000_000],
                              encoding="utf-8")
    print(f"Đã lưu: {out_path} ({Path(out_path).stat().st_size / 1024:.0f} KB)")
    print(summarize(eye))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
