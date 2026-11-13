import os, sys, time, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.runtime_lock import acquire, held_live_by_other


def ok(n, c, msg=''):
    print(('[PASS] ' if c else '[FAIL] ') + n + (f' {msg}' if msg and not c else ''))
    assert c

a = acquire(os.getpid(), client_id='client-A', owner_pid=os.getpid())
ok('owner claims its client', a is not None)
code = '''
import sys
sys.path.insert(0, r"%s")
from fila_bot.runtime_lock import acquire
try:
    acquire(7001, client_id="client-A", owner_pid=7001)
except OSError as exc:
    print(exc); raise SystemExit(11)
''' % str(Path(__file__).resolve().parents[1] / 'src')
import subprocess
p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
ok('second owner is refused', p.returncode == 11)
with tempfile.TemporaryDirectory(
        prefix='fila-lock-cwd-',
        dir=str(Path.home() / 'AppData/Local/hermes/cache/scratch')) as other_cwd:
    p_cwd = subprocess.run([sys.executable, '-c', code], capture_output=True,
                           text=True, cwd=other_cwd)
ok('same client lock is shared across launch directories', p_cwd.returncode == 11,
   p_cwd.stdout + p_cwd.stderr)
b = acquire(7002, client_id='client-B', owner_pid=os.getpid())
ok('different client may have a separate owner', b is not None)
b.close()
source = str(Path(__file__).resolve().parents[1] / 'src')
child_exit = subprocess.run([sys.executable, '-c', f'''\nimport sys\nsys.path.insert(0, r"{source}")\nfrom fila_bot.runtime_lock import acquire\nacquire(7003, client_id="client-C", owner_pid=7003)\n'''], capture_output=True, text=True)
c = acquire(7004, client_id='client-C', owner_pid=os.getpid())
ok('owner process exit releases its OS lock', child_exit.returncode == 0 and c is not None)
c.close()
a.close()

from unittest import mock
from fila_bot import single_instance
class ShimHandle:
    closed = False
    def close(self): self.closed = True
shim_handle = ShimHandle()
with mock.patch.object(single_instance, "find_client_window", return_value={"pid": 8080}), \
     mock.patch.object(single_instance.runtime_lock, "acquire", return_value=shim_handle) as lock_call:
    assert single_instance.acquire("legacy caller") is shim_handle
lock_call.assert_called_once_with(8080, client_id="eve-pid-8080", owner_pid=os.getpid())
single_instance.release()
ok('legacy lock API delegates to the client OS lock and releases it', shim_handle.closed)
ok('legacy lock API contains no PID-kill function', not hasattr(single_instance, '_kill_pid'))