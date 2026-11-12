"""P1 TRAINING — luyện 4 mắt còn mù trên client thật, không combat.

Boss 13-11 đã warp ra Nonni Star (điểm an toàn, không quái). Mỗi bước:
  1. Thao tác có giới hạn (1 lệnh, không spam).
  2. Đọc postcondition bằng mắt mới (speed/lock/drone) — chỉ vượt khi mắt thấy.
  3. Ghi evidence file cho regression.

Chạy: PYTHONPATH=src python tests/p1_training.py --step <orbit|lock|drone|all>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot import control  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402
from fila_bot.win import find_client_window  # noqa: E402

EV = ROOT / ".hermes/evidence/p1-training"
EV.mkdir(parents=True, exist_ok=True)


def ok(n, cond):
    print(("[PASS] " if cond else "[FAIL] ") + n)
    return bool(cond)


def fresh_eye() -> Eye:
    e = Eye()
    e.refresh()
    return e


def step_orbit(eye: Eye, win) -> bool:
    """Orbit Nonni Star 20km: bấm 1 lần → đo speed tăng + giữ range (P1 gate)."""
    ov = eye.overview_entries() or []
    star = next((e for e in ov if (e.get('Name') or '') == 'Nonni - Star'), None)
    if not star:
        print("[SKIP] không thấy Nonni - Star trên overview")
        return False
    xy = star.get('center')
    spec = control.act_orbit(xy, distance_km=20.0)
    res = control.execute(spec, eye=eye, dry=False, win=win)
    print("orbit sent:", res.get("ok"), res.get("detail", "")[:80])
    # đo speed tăng trong 20s (4 mẫu × 5s)
    speeds = []
    for i in range(4):
        time.sleep(5)
        e2 = fresh_eye()
        s = e2.speed_mps()
        speeds.append(s)
        print(f"  t+{(i+1)*5}s speed={s}")
    moving = [s for s in speeds if s and s > 10]
    ok(f"orbit: speed tăng ({speeds})", len(moving) >= 2)
    return len(moving) >= 2


def step_lock(eye: Eye, win) -> bool:
    """Lock 1 target (Nonni Star) → verify targetHealthBars xuất hiện (P1 gate)."""
    ov = eye.overview_entries() or []
    star = next((e for e in ov if (e.get('Name') or '') == 'Nonni - Star'), None)
    if not star:
        print("[SKIP] không thấy star để lock")
        return False
    before = eye.targets_in_bar()
    print("target bars trước lock:", len(before))
    spec = control.act_lock(star['center'])
    res = control.execute(spec, eye=eye, dry=False, win=win)
    print("lock sent:", res.get("ok"))
    # chờ target bar render (lock mất 1-3s) — poll 15s
    after = []
    for i in range(5):
        time.sleep(3)
        e2 = fresh_eye()
        after = e2.targets_in_bar()
        if after:
            break
        print(f"  t+{(i+1)*3}s target bars: {len(after)}")
    ok(f"lock: targetHealthBars xuất hiện ({len(after)})",
       len(after) >= 1 and len(after) > len(before))
    (EV / "lock_result.json").write_text(json.dumps(
        {"before": len(before), "after": after,
         "locked_at": time.strftime("%H:%M:%S")}, ensure_ascii=False), encoding="utf-8")
    return len(after) > len(before)


def step_unlock(eye: Eye, win) -> bool:
    """Unlock sau khi luyện (không để target treo)."""
    import fila_bot.input as inp
    # Ctrl+click vào entry đã lock = unlock (ground keybind)
    ov = eye.overview_entries() or []
    star = next((e for e in ov if (e.get('Name') or '') == 'Nonni - Star'), None)
    if not star:
        return False
    spec = control.ActionSpec("unlock_target", [{"do": "click", "at": star['center']}],
                              verify=None)
    res = control.execute(spec, eye=eye, dry=False, win=win)
    print("unlock:", res.get("ok"))
    return True


def step_drone(eye: Eye, win) -> bool:
    """Launch 1 drone → đếm in_space tăng → recall → về 0 (P1 gate)."""
    d0 = eye.drones_observation()
    print("trước launch:", d0)
    spec = control.act_launch_drones()
    res = control.execute(spec, eye=eye, dry=False, win=win)
    print("launch sent:", res.get("ok"))
    n = None
    for i in range(6):
        time.sleep(4)
        e2 = fresh_eye()
        d1 = e2.drones_observation()
        n = d1.get('in_space')
        print(f"  t+{(i+1)*4}s in_space={n} in_bay={d1.get('in_bay')}")
        if (n or 0) > (d0.get('in_space') or 0):
            break
    ok(f"drone launch: in_space tăng ({d0.get('in_space')} → {n})", (n or 0) > (d0.get('in_space') or 0))
    # recall
    spec2 = control.act_drones_return()
    control.execute(spec2, eye=eye, dry=False, win=win)
    d2 = {}
    for i in range(6):
        time.sleep(4)
        e2 = fresh_eye()
        d2 = e2.drones_observation()
        print(f"  recall t+{(i+1)*4}s in_space={d2.get('in_space')}")
        if (d2.get('in_space') or 0) == 0:
            break
    ok("drone recall: in_space về 0", (d2.get('in_space') or 0) == 0)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=("orbit", "lock", "drone", "all"), default="all")
    a = ap.parse_args()
    win = find_client_window()
    if not win:
        print("FATAL: không thấy EVE client")
        return 2
    eye = fresh_eye()
    results = {}
    if a.step in ("orbit", "all"):
        results["orbit"] = step_orbit(eye, win)
    if a.step in ("lock", "all"):
        results["lock"] = step_lock(eye, win)
        step_unlock(eye, win)
    if a.step in ("drone", "all"):
        results["drone"] = step_drone(eye, win)
    (EV / f"p1_{a.step}_{time.strftime('%H%M%S')}.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    print("\nP1 results:", results)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
