"""Observed per-NPC engagement state.

Mission hash and locators are NOT a stable identity when several objects share a
name.  This record keeps the object identity and facts returned by reading the
client.  Any update or write request must be checked against `allowed_actions`
and `can_action`; stale facts make both false rather than guessing.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any



@dataclass(frozen=True)
class NPCState:
    object_id: int
    display_name: str
    health_pct: int
    target_assigned: bool
    locked: bool
    being_repaired_by: int
    client_sha256: str
    collected_at: datetime
    evidence_id: str = ""
    source_kind: str = ""
    source_id: str = ""
    mission_offer_hash: str = ""
    mission_offer_node_id: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.object_id, int) or self.object_id <= 0: raise ValueError('object_id required')
        if not 0 <= self.health_pct <= 100: raise ValueError('health_pct')
        if not isinstance(self.target_assigned, bool) or not isinstance(self.locked, bool): raise TypeError('bool facts required')
        if not isinstance(self.being_repaired_by, int): raise TypeError('being_repaired_by')
        if not isinstance(self.client_sha256, str) or len(self.client_sha256)!=64: raise ValueError('client sha')
        if not isinstance(self.collected_at, datetime): raise TypeError('collected_at datetime')
        try: self.collected_at.isoformat()
        except ValueError as exc: raise ValueError('collected_at') from exc
        if not isinstance(self.mission_offer_hash,str) or len(self.mission_offer_hash)!=64: raise ValueError('mission hash')

    @property
    def can_use_mission(self) -> bool:
        return bool(self.mission_offer_hash and self.mission_offer_node_id)

    @property
    def can_action(self) -> bool:
        """Freshness is not accepted from a synthetic test clock without an observed frame."""
        now = datetime.now(self.collected_at.tzinfo) if self.collected_at.tzinfo else datetime.now()
        try: age=(now-self.collected_at).total_seconds()
        except Exception: age=10**9
        return self.can_use_mission and self.target_assigned and self.health_pct > 0 and 0 <= age <= 3650

    @property
    def allowed_actions(self) -> frozenset[str]:
        if not self.can_action: return frozenset()
        if self.being_repaired_by == self.object_id:
            return frozenset({'keep_away_from_npc','report_npc_damage'})
        return frozenset({'attack_npc','mark_npc_for_attention','request_repair_npc'})

    @property
    def damaged(self) -> bool:
        return self.being_repaired_by == self.object_id

    def snapshot(self) -> dict[str, Any]:
        return {'object_id': self.object_id, 'display_name': self.display_name,
                'health_pct': self.health_pct, 'target_assigned': self.target_assigned,
                'locked': self.locked, 'being_repaired_by': self.being_repaired_by,
                'client_sha256': self.client_sha256, 'collected_at': self.collected_at,
                'evidence_id': self.evidence_id, 'source_kind': self.source_kind,
                'source_id': self.source_id, 'mission_offer_hash': self.mission_offer_hash,
                'mission_offer_node_id': self.mission_offer_node_id,
                'can_use_mission': self.can_use_mission, 'can_action': self.can_action,
                'allowed_actions': sorted(self.allowed_actions), 'damaged': self.damaged}