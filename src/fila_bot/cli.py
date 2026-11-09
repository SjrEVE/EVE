"""CLI End-to-End cho fila-bot — Unified Launcher cho tat ca che do.

Usage:
    python -m fila_bot.cli status
    python -m fila_bot.cli distribution [--live] [--confirm-input] [--max-missions 5]
    python -m fila_bot.cli abyss [--live] [--confirm-input] [--filament "Tranquil Exotic Filament"]
    python -m fila_bot.cli inspect
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.eye import Eye  # noqa: E402
from fila_bot.ui_model import build_supervisor  # noqa: E402
from fila_bot.win import find_client_window  # noqa: E402
from fila_bot.world_snapshot import parse_world  # noqa: E402


def cmd_status(args) -> int:
    """Doc va in toan bo trang thai the gioi game qua WorldSnapshot."""
    print("=== DANG KET NOI EVE CLIENT... ===")
    win = find_client_window()
    if win:
        print(f"[OK] Cua so EVE: '{win['title']}' | Origin: {win['origin']} | Size: {win['size']}")
    else:
        print("[CANH BAO] Khong tim thay cua so exefile.exe (EVE Online).")

    try:
        eye = Eye(dll_path=args.dll)
        eye.refresh()
    except Exception as e:
        print(f"[LOI] Khong the khoi tao Eye reader: {e}")
        return 2

    snap = parse_world(eye)
    print("\n--- TRANG THAI THE GIOI GAME (WorldSnapshot) ---")
    print(f"Connection Lost (E-STOP) : {snap.connection_lost}")
    if snap.connection_lost:
        print("  -> PHAT HIEN POPUP MAT KET NOI! Bot se dung toan bo thao tac.")

    print(f"Trang thai vi tri         : {'DOCKED tai tram' if snap.docked else 'NGOAI KHONG GIAN (in space)'}")
    print(f"  He sao (Solar System)  : {snap.system} (Sec: {snap.security})")
    if snap.station:
        print(f"  Tram (Station)         : {snap.station}")

    if not snap.docked:
        print(f"Tau vu tru                : Toc do: {snap.speed_mps} m/s | Maneuver: {snap.maneuver}")
        if snap.ship_health:
            print(f"  HP                     : Shield {snap.ship_health.get('shield', 0)*100:.1f}% | Armor {snap.ship_health.get('armor', 0)*100:.1f}% | Hull {snap.ship_health.get('hull', 0)*100:.1f}%")
        print(f"  Target dang chon       : {snap.selected_name} | Nut thao tac: {list(snap.selected_buttons.keys())}")

    print(f"Route panel               : Dich: {snap.route.destination} | Jumps: {snap.route.jumps} | Markers: {snap.route.markers}")

    print(f"Agent Dialogue            : {'DANG MO' if snap.agent_dialog.open else 'Dong'}")
    if snap.agent_dialog.open:
        ad = snap.agent_dialog
        print(f"  Tieu de                : {ad.title}")
        print(f"  Nut san sang           : {list(ad.buttons.keys())}")
        if ad.pickup:
            print(f"  Pickup                 : {ad.pickup.get('name')}")
        if ad.dropoff:
            print(f"  Dropoff                : {ad.dropoff.get('name')}")
        print(f"  Link toa do            : Pickup {ad.pickup_link_xy} | Dropoff {ad.dropoff_link_xy}")

    print(f"Inventory                 : {'DANG MO' if snap.inventory.open else 'Dong'}")
    if snap.inventory.open:
        inv = snap.inventory
        print(f"  Hangars co san         : {list(inv.hangars.keys())}")
        if inv.capacity:
            print(f"  Capacity               : Used {inv.capacity.get('used')} m3 / Max {inv.capacity.get('max')} m3")
        print(f"  Items dem duoc         : {len(inv.items)}")
        for it in inv.items[:5]:
            print(f"    - {it.get('name')} tai {it.get('center')}")

    return 0


def cmd_distribution(args) -> int:
    """Chay bot Distribution (Courier) end-to-end."""
    is_live = bool(args.live)
    is_dry = not bool(args.confirm_input)

    print("=" * 60)
    print("FILA-BOT — DISTRIBUTION COURIER MISSION RUNNER")
    print(f"Che do: {'LIVE (Client that)' if is_live else 'SIM (Gia lap test)'}")
    print(f"Thao tac: {'THUC THI PHIM/CHUOT THAT' if not is_dry else 'DRY-RUN (Chi log, an toan)'}")
    print(f"Gioi han: {args.max_missions or 'Vo han'} nhiem vu")
    print("=" * 60)

    if is_live and not is_dry:
        win = find_client_window()
        if not win:
            print("FATAL: Khong tim thay cua so EVE client. Khong the chay che do confirm-input.")
            return 2

    sup = build_supervisor(
        mode="distribution",
        sim=not is_live,
        dry=is_dry,
        dll=args.dll,
        max_hours=args.max_hours,
    )

    if args.max_missions and hasattr(sup.mode, "max_missions"):
        sup.mode.max_missions = args.max_missions

    sup.start_thread(tick_interval=args.tick)
    sup.send("START")

    print("\nBot da bat dau. Nhan Ctrl+C de dung an toan...")
    try:
        while True:
            time.sleep(1.0)
            st = sup.mode.status() if hasattr(sup.mode, "status") else {}
            phase = getattr(sup.mode, "phase", sup.state)
            print(f"[{time.strftime('%H:%M:%S')}] State: {sup.state} | Phase: {phase} | Runs: {st.get('runs', 0)} | Declined: {st.get('declined', 0)}")
            if sup.state in ("STOPPED", "BLOCKED"):
                print(f"\nBot da dung lai: {sup.state}. Ly do: {st.get('blocked')}")
                break
    except KeyboardInterrupt:
        print("\nNhan lenh dung tu nguoi dung... Dang thu hoi phan cung va dung sach.")
        sup.send("STOP")
        time.sleep(1.0)
        sup.shutdown()
        print("Da shutdown hoan tat.")

    return 0


def cmd_abyss(args) -> int:
    """Chay bot Abyssal Deadspace end-to-end."""
    is_live = bool(args.live)
    is_dry = not bool(args.confirm_input)

    print("=" * 60)
    print("FILA-BOT — ABYSSAL DEADSPACE RUNNER")
    print(f"Che do: {'LIVE (Client that)' if is_live else 'SIM (Gia lap test)'}")
    print(f"Thao tac: {'THUC THI PHIM/CHUOT THAT' if not is_dry else 'DRY-RUN (Chi log, an toan)'}")
    print(f"Filament: {args.filament}")
    print("=" * 60)

    sup = build_supervisor(
        mode="abyss",
        sim=not is_live,
        dry=is_dry,
        dll=args.dll,
        max_hours=args.max_hours,
    )

    sup.start_thread(tick_interval=args.tick)
    sup.send("START")

    print("\nBot Abyss da bat dau. Nhan Ctrl+C de dung an toan...")
    try:
        while True:
            time.sleep(1.0)
            phase = getattr(sup.mode, "phase", sup.state)
            print(f"[{time.strftime('%H:%M:%S')}] State: {sup.state} | Phase: {phase}")
            if sup.state in ("STOPPED", "BLOCKED"):
                print(f"\nBot Abyss da dung: {sup.state}")
                break
    except KeyboardInterrupt:
        print("\nNhan lenh dung... Dang shutdown an toan.")
        sup.send("STOP")
        time.sleep(1.0)
        sup.shutdown()

    return 0


def cmd_inspect(args) -> int:
    """Mo hoac in link toi Visual DOM Inspector."""
    p = ROOT / "tools" / "inspector.html"
    print("\nVisual EVE UI Tree Inspector:")
    print(f"Duong dan file: {p.resolve()}")
    print("\nDe xem truc quan cay DOM va bounding box cua EVE client:")
    print("1. Mo file tren bang bat ky trinh duyet nao (Chrome, Edge, Firefox).")
    print("2. Keo tha bat ky file dump .json nao trong thu muc 'dumps/' hoac 'tests/fixtures/' vao.")
    print("3. Hover chuot len canvas de xem type, _name, text, center toa do.")
    return 0


def main():
    p = argparse.ArgumentParser(description="fila-bot Unified End-to-End CLI")
    p.add_argument("--dll", default=None, help="Duong dan DLL doc bo nho")
    sub = p.add_subparsers(dest="subcommand", required=True)

    # status
    p_stat = sub.add_parser("status", help="Xem trang thai the gioi game qua WorldSnapshot")
    p_stat.set_defaults(func=cmd_status)

    # distribution
    p_dist = sub.add_parser("distribution", help="Chay bot Distribution Courier mission")
    p_dist.add_argument("--live", action="store_true", help="Chay tren client EVE that (mac dinh la sim)")
    p_dist.add_argument("--confirm-input", action="store_true", help="Thuc thi click va phim that (mac dinh chi log)")
    p_dist.add_argument("--max-missions", type=int, default=None, help="So mission toi da")
    p_dist.add_argument("--max-hours", type=float, default=4.0, help="So gio chay toi da")
    p_dist.add_argument("--tick", type=float, default=0.5, help="Tick interval (giay)")
    p_dist.set_defaults(func=cmd_distribution)

    # abyss
    p_aby = sub.add_parser("abyss", help="Chay bot Abyssal Deadspace")
    p_aby.add_argument("--live", action="store_true", help="Chay tren client EVE that (mac dinh la sim)")
    p_aby.add_argument("--confirm-input", action="store_true", help="Thuc thi click va phim that (mac dinh chi log)")
    p_aby.add_argument("--filament", default="Tranquil Exotic Filament", help="Ten filament can chay")
    p_aby.add_argument("--max-hours", type=float, default=4.0, help="So gio chay toi da")
    p_aby.add_argument("--tick", type=float, default=0.3, help="Tick interval (giay)")
    p_aby.set_defaults(func=cmd_abyss)

    # inspect
    p_ins = sub.add_parser("inspect", help="Mo hoac in thong tin UI inspector")
    p_ins.set_defaults(func=cmd_inspect)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
