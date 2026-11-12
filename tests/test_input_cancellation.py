"""SYNTHETIC Win32 API spy: release tracked keys and cancel in-progress input."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fila_bot import input as inp
class User32:
    def __init__(self): self.keys=[]; self.mouse=[]
    def GetAsyncKeyState(self,k): return 0
    def keybd_event(self,k,scan,flags,extra): self.keys.append((k,flags))
    def mouse_event(self,flags,*rest): self.mouse.append(flags)
u=User32(); inp._ACTIVE_HOLDS.add(0x51)
inp.release_all(user32=u)
assert (0x51,2) in u.keys, 'Q held for approach was not released by E-STOP'
print('[PASS] release_all releases tracked non-modifier keys too')
