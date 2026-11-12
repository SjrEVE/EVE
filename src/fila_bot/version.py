"""fila-bot — một nguồn sự thật duy nhất cho phiên bản.

Đọc priority:
1. env FILA_BOT_VERSION      (build script ghi đè khi đóng gói)
2. VERSION file cạnh package  (ghi ở repo root)
3. "0.0.0-dev"                (chạy từ source không VERSION)

Format: MAJOR.MINOR.PATCH + nhãn build tuỳ chọn ("-live" = đang chạy live).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_FALLBACK = "0.0.0-dev"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def _repo_root() -> Path:
    # src/fila_bot/version.py -> repo root là 2 cấp trên package
    return Path(__file__).resolve().parents[2]


def read_version() -> str:
    env = __import__("os").environ.get("FILA_BOT_VERSION", "").strip()
    if env and SEMVER_RE.match(env):
        return env
    vf = _repo_root() / "VERSION"
    if vf.is_file():
        txt = vf.read_text(encoding="utf-8-sig").strip()
        if txt and SEMVER_RE.match(txt):
            return txt
    return _FALLBACK


def parse(v: str) -> tuple[int, int, int, str | None]:
    m = SEMVER_RE.match(v)
    if not m:
        return (0, 0, 0, None)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))


def version_tuple() -> tuple[int, int, int, str | None]:
    return parse(read_version())


def short() -> str:
    """'v1.4.0' — dùng cho tiêu đề cửa sổ."""
    return "v" + read_version()


def banner() -> str:
    """Dòng banner 'FILA-BOT vX.Y.Z (…)' — CLI in đầu mỗi mode."""
    info = build_info()
    tag = f" ({info['label']})" if info["label"] else ""
    return f"FILA-BOT {short()} ({info['commit']}{tag})"


def build_info() -> dict:
    """Commit + nhãn build từ BUILD_INFO.json (do build script sinh)."""
    p = _repo_root() / "BUILD_INFO.json"
    out = {"commit": "unknown", "label": "", "built_at": ""}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            out["commit"] = str(data.get("commit", out["commit"]))[:12]
            out["label"] = str(data.get("label", ""))
            out["built_at"] = str(data.get("built_at", ""))
        except Exception:
            pass
    return out


def assert_min(major: int, minor: int = 0) -> None:
    """Mode mới dùng: chặn chạy trên bản quá cũ (session/profile tương thích)."""
    v = version_tuple()
    if (v[0], v[1]) < (major, minor):
        raise SystemExit(
            f"[VERSION] Ban {read_version()} qua cu: mode nay can >={major}.{minor}."
        )


if __name__ == "__main__":
    print(json.dumps({"version": read_version(),
                      "tuple": version_tuple(),
                      "build": build_info()}, indent=2))
