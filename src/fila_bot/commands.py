"""Command DSL v1 — whitelist cứng theo FC_PROTOCOL.md v1 (keybind thật của EVE)."""
from __future__ import annotations

from typing import Any


class CommandError(ValueError):
    pass


# Mỗi cmd: None (không arg) hoặc list các dạng hợp lệ (kiểu, biên_or_whitelist)
COMMAND_SPEC: dict[str, dict[str, Any]] = {
    "TARGET":     {"arg": [(str, ("nearest",)), (int, (0, 11))]},
    "APPROACH":   {"arg": [(str, None), (int, (0, 11))]},
    "ORBIT":      {"arg": [(int, (1, 100000))]},
    "KEEP_RANGE": {"arg": [(int, (1, 100000))]},
    "ACTIVATE":   {"arg": [(int, (1, 8))]},
    "DEACTIVATE": {"arg": [(int, (1, 8))]},
    "RELOAD":     {"arg": None},
    "STOP":       {"arg": None},
    "SPEED":      {"arg": [(int, (0, 100))]},
    "GATE":       {"arg": None},
    "DOCK":       {"arg": None},
    "UNDOCK":     {"arg": None},
    "JUMP":       {"arg": [(str, None)]},
    "FILA":       {"arg": [(str, None)]},
    "CONFIRM":    {"arg": None},
    "LOOT":       {"arg": None},
    "SET":        {"arg": [(str, None)]},   # "param value"
    "SET_PHASE":  {"arg": [(str, None)]},   # FC báo bot phase (ROOM1_FIGHT → ROOM1_CLEARED)
    "HOLD":       {"arg": None},
    "ABORT":      {"arg": None},
    "STATUS":     {"arg": None},
}

# Lệnh không arg — bot bỏ qua validation arg
NO_ARG_CMDS = frozenset(k for k, v in COMMAND_SPEC.items() if v["arg"] is None)

# param: (lo, hi, default) — lo/hi None = bool
SET_PARAMS: dict[str, tuple] = {
    "escape_hp":       (0.05, 0.90, 0.25),
    "unknown_timeout": (10.0, 300.0, 45.0),
    "orbit_default":   (500, 20000, 2500),
    "humanize":        (None, None, True),
    "tick_interval":   (0.1, 2.0, 0.3),
    "warn_timer_left": (60, 1200, 300),
}


def validate(cmd: str, arg: Any) -> Any:
    """Trả arg chuẩn hoá hoặc raise CommandError(reason)."""
    spec = COMMAND_SPEC.get(cmd)
    if spec is None:
        raise CommandError("not in whitelist")
    allowed = spec["arg"]
    if allowed is None:
        if arg in (None, "", {}):
            return None
        raise CommandError(f"{cmd} takes no arg")
    if cmd == "SET":
        if not isinstance(arg, str) or len(arg.split()) != 2:
            raise CommandError("SET needs 'param value'")
        param, value_s = arg.split()
        if param not in SET_PARAMS:
            raise CommandError(f"unknown param '{param}'")
        try:
            value = float(value_s)
        except ValueError:
            raise CommandError(f"param '{param}' value không phải số")
        lo, hi, _default = SET_PARAMS[param]
        if lo is not None and not (lo <= value <= hi):
            raise CommandError(f"param '{param}' out of bounds {lo}..{hi}")
        return (param, value)
    kinds = allowed if isinstance(allowed, list) else [allowed]
    last: Exception | None = None
    for kind in kinds:
        try:
            return _try_kind(kind, arg)
        except (CommandError, ValueError, TypeError) as e:
            last = e
            continue
    if isinstance(last, CommandError):   # lỗi domain (bounds/whitelist) đưa nguyên văn
        raise last
    raise CommandError(str(last) if last else "arg sai kiểu")


def _try_kind(kind: tuple, arg: Any) -> Any:
    """kind = (kiểu, biên): (str, ("nearest",)) | (int, (0,11)) | (str, None)."""
    ktype, bound = kind
    if ktype is str:
        if bound is not None and arg not in bound:
            raise CommandError("arg ngoài whitelist")
        return str(arg)
    if ktype is int:
        v = int(arg)
        if bound is not None and not (isinstance(bound, tuple) and bound[0] <= v <= bound[1]):
            raise CommandError(f"arg out of bounds {bound[0]}..{bound[1]}")
        return v
    raise CommandError("bad spec")
