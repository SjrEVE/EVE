"""No LIVE initialization before an explicitly configured mission profile."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fila_bot.ui_model import build_supervisor, ModeUnavailable
with patch('fila_bot.eye.Eye', side_effect=AssertionError('unsafe: reader initialized before profile validation')):
    try:
        build_supervisor('security', sim=False, dry=False)
    except ModeUnavailable as e:
        assert 'profile' in str(e).lower(), e
    else:
        raise AssertionError('LIVE without profile must be rejected')
print('[PASS] LIVE security requires explicit profile before reader initialization')

# Invalid explicit configuration is also rejected before native initialization.
with patch('fila_bot.eye.Eye', side_effect=AssertionError('reader loaded with incomplete profile')):
    try:
        build_supervisor('security', sim=False, dry=False, profile={})
    except ModeUnavailable as e:
        assert 'profile' in str(e).lower(), e
    else:
        raise AssertionError('empty profile must fail validation')
print('[PASS] incomplete explicit profile is rejected before native initialization')

import subprocess, os
r = subprocess.run([sys.executable, '-m', 'fila_bot.cli', 'security', '--help'],
                   env={**os.environ, 'PYTHONPATH':str(Path(__file__).resolve().parents[1] / 'src')},
                   capture_output=True, text=True, timeout=10)
assert r.returncode == 0 and '--profile' in r.stdout, r.stdout
print('[PASS] explicit profile is available at the production CLI entrypoint')
