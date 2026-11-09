"""Behavior Tree core — thay the nhang if/else FSM bang cay uu tien co chuan.
Node dang: (name, kind, children/actions)
kind: 'sel' (Selector: chay node dau tien thanh cong), 'seq' (Sequence: chay het),
      'par' (Parallel: chay tat ca), 'cond' (check dieu kien), 'act' (hanh dong).
Moi node tick() tra ve: SUCCESS | FAILURE | RUNNING.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable


class Status(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


Ctx = dict[str, Any]          # world snapshot + bot state
Tick = Callable[[Ctx], Status]


class Node:
    def __init__(self, name: str, kind: str, children: list["Node"] | None = None,
                 run: Tick | None = None) -> None:
        self.name = name
        self.kind = kind
        self.children = children or []
        self.run = run
        self._running_idx = 0

    def tick(self, ctx: Ctx) -> Status:
        if self.kind == "cond":
            return self.run(ctx) if self.run else Status.FAILURE
        if self.kind == "act":
            return self.run(ctx) if self.run else Status.FAILURE
        if self.kind == "sel":
            return self._tick_selector(ctx)
        if self.kind == "seq":
            return self._tick_sequence(ctx)
        if self.kind == "par":
            return self._tick_parallel(ctx)
        return Status.FAILURE

    def _tick_selector(self, ctx: Ctx) -> Status:
        """Selector co nho: chay tu node RUNNING truoc do (khong re-check node o truoc)."""
        for i in range(self._running_idx, len(self.children)):
            st = self.children[i].tick(ctx)
            if st == Status.RUNNING:
                self._running_idx = i
                return Status.RUNNING
            if st == Status.SUCCESS:
                self._running_idx = 0
                return Status.SUCCESS
        self._running_idx = 0
        return Status.FAILURE

    def _tick_sequence(self, ctx: Ctx) -> Status:
        for i, ch in enumerate(self.children):
            st = ch.tick(ctx)
            if st == Status.RUNNING:
                return Status.RUNNING
            if st == Status.FAILURE:
                return Status.FAILURE
        return Status.SUCCESS

    def _tick_parallel(self, ctx: Ctx) -> Status:
        """Parallel: chay TAT CA con; RUNNING neu co bat ky con nao RUNNING."""
        any_running = False
        for ch in self.children:
            st = ch.tick(ctx)
            if st == Status.RUNNING:
                any_running = True
        return Status.RUNNING if any_running else Status.SUCCESS

    def dump(self, depth: int = 0) -> str:
        lines = ["  " * depth + f"{self.kind}:{self.name}"]
        for ch in self.children:
            lines.append(ch.dump(depth + 1))
        return "\n".join(lines)


def cond(name: str, fn: Tick) -> Node:
    return Node(name, "cond", run=fn)


def act(name: str, fn: Tick) -> Node:
    return Node(name, "act", run=fn)


def sel(name: str, children: list[Node]) -> Node:
    return Node(name, "sel", children=children)


def seq(name: str, children: list[Node]) -> Node:
    return Node(name, "seq", children=children)


def par(name: str, children: list[Node]) -> Node:
    return Node(name, "par", children=children)


def _ctx_get(ctx: Ctx, path: str, default: Any = None) -> Any:
    cur: Any = ctx
    for k in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur


def is_flag(path: str) -> Tick:
    """Cond helper: ctx[path] truthy."""
    return lambda ctx: Status.SUCCESS if _ctx_get(ctx, path) else Status.FAILURE


def lt(path: str, threshold: float) -> Tick:
    """Cond helper: ctx[path] < threshold."""
    return lambda ctx: (Status.SUCCESS if (v := _ctx_get(ctx, path)) is not None
                        and isinstance(v, (int, float)) and v < threshold else Status.FAILURE)


def gt(path: str, threshold: float) -> Tick:
    """Cond helper: ctx[path] > threshold."""
    return lambda ctx: (Status.SUCCESS if (v := _ctx_get(ctx, path)) is not None
                        and isinstance(v, (int, float)) and v > threshold else Status.FAILURE)


def eq(path: str, value: Any) -> Tick:
    return lambda ctx: Status.SUCCESS if _ctx_get(ctx, path) == value else Status.FAILURE


def in_list(path: str, values: tuple | list) -> Tick:
    return lambda ctx: Status.SUCCESS if _ctx_get(ctx, path) in values else Status.FAILURE


def do_log_action(action_name: str) -> Tick:
    """Act helper: ghi action vao ctx['actions'] (danh sach FSM/executor se thuc thi)."""
    def _do(ctx: Ctx) -> Status:
        actions = ctx.setdefault("actions", [])
        actions.append({"do": action_name})
        return Status.SUCCESS
    return _do
