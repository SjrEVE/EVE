"""Synthetic blocked-refresh fault; no game process/input is touched."""
import sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fila_bot.runner import Supervisor
from fila_bot.modes import Mode

class Probe(Mode):
    name='probe'
    def tick(self,world): return [{'do':'click','at':(10,20)}]
entered=threading.Event(); unblock=threading.Event(); released=threading.Event(); calls=[]
def refresh():
    entered.set(); unblock.wait(3); return {}
s=Supervisor(Probe(),refresh=refresh,execute=lambda a:calls.extend(a),release_all=released.set)
s.start_thread(.01); s.send('START')
assert entered.wait(1),'probe did not enter refresh'
t0=time.monotonic(); s.send('ESTOP'); prompt=released.wait(.35); elapsed=time.monotonic()-t0
unblock.set(); s.shutdown(); time.sleep(.03)
assert prompt and elapsed < .5, f'E-STOP waited for reader: {elapsed}'
assert not calls, f'stale tick executed after E-STOP: {calls}'
print('[PASS] E-STOP releases promptly while refresh blocks; stale tick cannot execute')

# Same blocked reader, but trigger the independent hotkey watchdog.
entered.clear(); unblock.clear(); released.clear(); calls.clear(); hotkey=threading.Event()
s=Supervisor(Probe(),refresh=refresh,execute=lambda a:calls.extend(a),release_all=released.set,
             kill_switch=hotkey.is_set)
s.start_thread(.01); s.send('START'); assert entered.wait(1)
hotkey.set(); prompt=released.wait(.35); unblock.set(); s.shutdown(); time.sleep(.03)
assert prompt and not calls, 'hotkey must not wait for the reader loop'
print('[PASS] hotkey watchdog interrupts a blocked reader independently of tick')
