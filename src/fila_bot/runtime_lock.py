"""Exclusion locks keyed by the actual EVE client, not process identity alone."""
import os
from pathlib import Path

LOCK_FILENAME = 'fila-bot.client.lock'


def _lock_root() -> Path:
    """Use one per-user location so separate working directories share ownership."""
    if os.name == 'nt':
        root = os.environ.get('LOCALAPPDATA')
        return (Path(root) if root else Path.home() / 'AppData' / 'Local') / 'fila-bot' / 'locks'
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if runtime:
        return Path(runtime) / 'fila-bot' / 'locks'
    return Path.home() / '.local' / 'state' / 'fila-bot' / 'locks'


def path_for(pid: int) -> Path:
    return _client_path(pid=pid)


def _client_path(client_id=None, pid: int | None = None) -> Path:
    safe = ''.join(ch if ch.isalnum() or ch in '-_.' else '_' for ch in str(client_id or f'pid-{pid}'))
    return _lock_root() / f'{LOCK_FILENAME}.{safe}'


def _lock(handle) -> None:
    if os.name == 'nt':
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def acquire(pid: int, *, client_id=None, owner_pid: int | None = None,
            owner_token: str | None = None):
    """Claim one owner per client. The OS lock releases on process exit."""
    path = _client_path(client_id, pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, 'a+b')
    _lock(handle)
    handle.seek(0); handle.truncate()
    handle.write((owner_token or 'client=' + str(client_id or 'unknown')
                  + ' owner=' + str(owner_pid or pid)).encode() + b'\n')
    handle.flush()
    return handle


def held_live_by_other(pid: int, *, client_id=None, timeout: float = 0.25) -> dict:
    """Report an owner currently holding a lock. Never kills a recorded PID."""
    path = _client_path(client_id, pid)
    if not path.is_file():
        return {}
    try:
        handle = open(path, 'a+b')
        _lock(handle)
    except OSError:
        handle = open(path, 'rb')
        return {'pid': pid, 'owner': handle.read().decode(errors='replace').strip(),
                'held': True}
    if os.name == 'nt':
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    handle.close()
    return {}