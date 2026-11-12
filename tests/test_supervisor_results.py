"""Supervisor must return execution results to the mode for read-back/state."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.runner import Supervisor

class Mode:
    name = "probe"
    phase = "X"
    stop_requested = False
    at_safe_point = False
    def __init__(self): self.got = None
    def tick(self, world): return [{"do": "probe"}]
    def on_action_results(self, results): self.got = results
    def status(self): return {"phase": self.phase}

m = Mode()
sup = Supervisor(m, refresh=lambda: {"ok": True},
                 execute=lambda acts: [{"ok": False, "status": "FAILED"}])
sup.send("START")
sup.step()
assert m.got == [{"ok": False, "status": "FAILED"}], m.got
print('[PASS] mode receives executor results, including failures')

sup.send("ESTOP")
print('\nKet qua: 1 PASS / 0 FAIL')
