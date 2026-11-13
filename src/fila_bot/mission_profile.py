"""Explicit owner configuration. Empty/unknown fields never authorize LIVE input."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_build(data: dict[str, Any], client_exe: str | Path,
                 reader_dll: str | Path) -> list[str]:
    """Compare pinned hashes with the binaries actually about to run."""
    errors = []
    for key, path in (('client_sha256', client_exe), ('reader_sha256', reader_dll)):
        try:
            actual = sha256_file(path)
        except OSError as exc:
            errors.append(f'{key}: cannot read {path}: {exc}')
            continue
        if actual != data.get(key):
            errors.append(f'{key} mismatch: profile {data.get(key)} != actual {actual}')
    return errors


def preflight_world(data: dict[str, Any], world: dict[str, Any],
                    window_title: str | None = None) -> list[str]:
    """Read-only checks before the first input. UNKNOWN fails closed."""
    errors = []
    errors.extend(profile_errors(data))
    if window_title is not None:
        title = window_title.lower()
        if 'eve - ' not in title and title != 'eve':
            errors.append(f'window is not an EVE client: {window_title!r}')
        elif data.get('character') and data['character'].strip().lower() not in title:
            errors.append(f'window title does not contain profile character {data["character"]!r}')
    if world.get('location_known') is not True:
        errors.append('location is UNKNOWN (reader has no valid solar system)')
    if world.get('connection_lost') is True:
        errors.append('client reports Connection Lost')
    ship = world.get('ship_hull')
    if ship and data.get('ship_hull') and str(ship).casefold() != str(data['ship_hull']).casefold():
        errors.append(f'ship hull mismatch: profile {data["ship_hull"]!r} != observed {ship!r}')
    return errors


def load_profile(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, (str, Path)):
        data = json.loads(Path(source).read_text(encoding='utf-8-sig'))
    else:
        data = source
    if not isinstance(data, dict):
        raise ValueError('mission profile must be a JSON object')
    return dict(data)


def profile_errors(data: dict[str, Any]) -> list[str]:
    errors = []
    for key in ('character', 'agent_name', 'home_station', 'ship_hull'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f'{key} is unconfigured')
    if not isinstance(data.get('agent_id'), str) or not re.fullmatch(r'[0-9]+', data['agent_id']):
        errors.append('agent_id must be an exact decimal string')
    for key in ('client_sha256', 'reader_sha256'):
        if not isinstance(data.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', data[key]):
            errors.append(f'{key} must pin the inspected build')
    if type(data.get('level')) is not int or data['level'] not in (1, 2):
        errors.append('profile level must be 1 or 2 (L2 opened by owner 2026-11-13)')
    if data.get('accept_policy') != 'non_anomic':
        errors.append('accept_policy must preserve non_anomic owner policy')
    slots = data.get('weapon_slots', [1, 2, 3, 4])
    if (not isinstance(slots, list) or not slots
            or any(type(s) is not int or not 1 <= s <= 8 for s in slots)
            or len(set(slots)) != len(slots)):
        errors.append('weapon_slots must be a non-empty list of unique integers 1..8')
    # Propulsion/defense slots are what make "turn on the tank" possible at all.
    # Live 11-12: the HUD reported null for the Afterburner and both hardeners,
    # so the bot entered the site with no tank and no propulsion.
    ab_slot = data.get('afterburner_slot')
    if ab_slot is not None and (type(ab_slot) is not int or not 1 <= ab_slot <= 8):
        errors.append('afterburner_slot must be an integer 1..8')
    defense = data.get('defense_slots')
    if defense is not None and (
            not isinstance(defense, list)
            or any(type(s) is not int or not 1 <= s <= 8 for s in defense)
            or len(set(defense)) != len(defense)):
        errors.append('defense_slots must be a list of unique integers 1..8')
    elif isinstance(defense, list) and ab_slot is not None and ab_slot in defense:
        errors.append('defense_slots must not repeat afterburner_slot')
    path = data.get('session_file')
    if path is not None and not isinstance(path, str):
        errors.append('session_file must be a path string')
    elif isinstance(path, str) and not path.strip():
        errors.append('session_file must not be empty')
    # Hệ của trạm nhà: cần để tự nhảy cổng về khi mission kết thúc ở hệ khác
    # (ground 11-12: tàu bị bỏ lại ở Elonaya, trạm nhà ở Piak).
    home_system = data.get('home_system')
    if home_system is not None and (not isinstance(home_system, str)
                                    or not home_system.strip()):
        errors.append('home_system must be a non-empty system name')
    return errors
