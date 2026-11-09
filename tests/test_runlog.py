"""Test RunLog (runlog.py): nhat ky session START->IDLE vao runs/*.jsonl + read_stats + UI stats.

Chay: PYTHONPATH=src python tests/test_runlog.py
"""
from __future__ import annotations

import json
import queue
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fila_bot.modes import Mode                    # noqa: E402
from fila_bot.runner import Supervisor             # noqa: E402
from fila_bot.runlog import RunLog, read_stats     # noqa: E402
from fila_bot.ui_model import UiModel              # noqa: E402


def ok(name: str) -> None:
    print(f"[PASS] {name}")


class FakeMode(Mode):
    name = "fake"

    def __init__(self) -> None:
        super().__init__()
        self.ticks = 0
        self.safe = False
        self.boom = False
        self.safe_after_ticks: int | None = None

    def tick(self, world):
        if self.boom:
            raise RuntimeError("boom")
        self.ticks += 1
        if self.stop_requested and self.safe_after_ticks is not None:
            self.safe_after_ticks -= 1
            if self.safe_after_ticks <= 0:
                self.safe = True
        return [("noop",)]

    @property
    def at_safe_point(self):
        return self.safe

    @property
    def in_no_escape(self):
        return False


def drain(sup) -> list[dict]:
    out = []
    while True:
        try:
            out.append(sup.evt_q.get_nowait())
        except queue.Empty:
            return out


def tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="fila_runlog_"))


def lines_of(d: Path) -> list[dict]:
    files = sorted(d.glob("*.jsonl"))
    assert len(files) == 1, files
    return [json.loads(x) for x in files[0].read_text(encoding="utf-8").splitlines()]


# 1. session_start/end ghi JSONL du truong, dur_s theo clock inject
d1 = tmpdir()
clk = {"t": 100.0}
rl = RunLog(d1, clock=lambda: clk["t"])
rl.session_start("fake")
clk["t"] = 300.0
rl.session_end("het gio", ticks=7, status={"runs": 3, "mode": "fake"})
st, en = lines_of(d1)
assert st["type"] == "session_start" and st["mode"] == "fake"
assert isinstance(st["t"], (int, float))
assert en["type"] == "session_end" and en["reason"] == "het gio"
assert en["ticks"] == 7 and en["dur_s"] == 200.0
assert en["status"]["runs"] == 3 and en["mode"] == "fake"
ok("session_start/end ghi JSONL du truong")

# 2. end ma chua start -> khong ghi gi
d2 = tmpdir()
RunLog(d2).session_end("x")
assert not list(d2.glob("*.jsonl"))
ok("end chua start -> khong ghi")

# 3. Supervisor: START..STOP..IDLE ghi start + end (reason, ticks, status, dur)
d3 = tmpdir()
now = {"t": 0.0}
m = FakeMode()
sup = Supervisor(m, release_all=lambda: None,
                 runlog=RunLog(d3, clock=lambda: now["t"]), clock=lambda: now["t"])
sup.send("START"); sup.step()
m.safe_after_ticks = 2
sup.send("STOP"); sup.step()
now["t"] = 42.0
sup.step(); sup.step()
assert sup.state == "IDLE", sup.state
st, en = lines_of(d3)
assert st["type"] == "session_start" and st["mode"] == "fake"
assert en["type"] == "session_end" and en["reason"] == "đã tới safe point"
assert en["ticks"] >= 1 and en["dur_s"] == 42.0
assert en["status"].get("mode") == "fake"
ok("Supervisor STOP an toan -> start + end dung reason")

# 4. E-STOP dong session
d4 = tmpdir()
m = FakeMode()
sup = Supervisor(m, release_all=lambda: None, runlog=RunLog(d4))
sup.send("START"); sup.step()
sup.send("ESTOP"); sup.step()
assert sup.state == "IDLE"
st, en = lines_of(d4)
assert en["type"] == "session_end" and en["reason"] == "E-STOP"
ok("E-STOP -> session_end")

# 5. crash ghi crash, session van mo; ESTOP sau do dong
d5 = tmpdir()
m = FakeMode()
sup = Supervisor(m, release_all=lambda: None, runlog=RunLog(d5))
sup.send("START"); sup.step()
m.boom = True; sup.step()
assert sup.state == "PAUSED"
sup.send("ESTOP"); sup.step()
recs = lines_of(d5)
assert [r["type"] for r in recs] == ["session_start", "crash", "session_end"], recs
assert "boom" in recs[1]["error"]
ok("crash ghi crash + session dong o ESTOP sau do")

# 6. IDLE khong ghi gi
d6 = tmpdir()
m = FakeMode()
sup = Supervisor(m, release_all=lambda: None, runlog=RunLog(d6))
sup.step(); sup.send("PAUSE"); sup.step(); sup.send("FLY"); sup.step()
assert not list(d6.glob("*.jsonl"))
ok("IDLE / lenh la -> khong ghi")

# 7. 2 session lien tiep + read_stats tong hop
d7 = tmpdir()
rl = RunLog(d7, clock=lambda: 0.0)
rl.session_start("fake"); rl.session_end("đã tới safe point", ticks=3, status={"runs": 3})
rl.session_start("fake"); rl.crash("boom"); rl.session_end("E-STOP", ticks=1, status={"runs": 2})
s = read_stats(d7)
assert s["sessions"] == 2 and s["completed"] == 5, s
assert s["crashes"] == 1 and s["last_reason"] == "E-STOP", s
assert s["modes"] == {"fake": 2}, s
ok("read_stats tong hop sessions/completed/crashes")

# 8. read_stats bo qua line hong, dir khong ton tai tra zeros
(d7 / sorted(p.name for p in d7.glob("*.jsonl"))[0]).open("a", encoding="utf-8").write(
    "khong phai json\n")
s = read_stats(d7)
assert s["sessions"] == 2 and s["completed"] == 5
assert read_stats(tmpdir() / "khong_co")["sessions"] == 0
ok("read_stats nhan line hong + dir thieu")

# 9. UiModel.view() phoi stats (runs_dir inject)
m = UiModel(runs_dir=str(d7))
v = m.view()
assert v["stats"]["sessions"] == 2 and v["stats"]["completed"] == 5, v["stats"]
ok("UiModel.view() co stats")

# 10. runs_dir khong ton tai -> stats zeros, khong crash (khong duoc depends repo runs/
# vì test khác (test_ui_model) tạo session thật vào runs/ mặc định)
v = UiModel(runs_dir=str(tmpdir() / "khong_ton_tai")).view()
assert v["stats"]["sessions"] == 0
ok("runs_dir thieu -> stats zeros an toan")

# 11. Supervisor resume PAUSED khong mo session moi
d11 = tmpdir()
m = FakeMode()
sup = Supervisor(m, release_all=lambda: None, runlog=RunLog(d11))
sup.send("START"); sup.step()
sup.send("PAUSE"); sup.step()
sup.send("RESUME"); sup.step()
assert [r["type"] for r in lines_of(d11)] == ["session_start"]
ok("PAUSE/RESUME khong mo session moi")

print("ALL OK test_runlog")
