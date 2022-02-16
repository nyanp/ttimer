from __future__ import annotations
import copy
import time
from contextlib import ContextDecorator
from typing import Dict, List, Optional, Tuple

from anytree import NodeMixin, RenderTree
from tabulate import tabulate


class StopWatch:
    def __init__(self, name: str):
        self.name = name
        self.start = time.time()
        self.elapsed = 0.0

    def stop(self) -> None:
        self.elapsed = time.time() - self.start


class Record(NodeMixin):
    def __init__(self, name: str, count: int = 0, time: float = 0.0, own_time: float = 0.0,
                 parent: Optional[Record] = None):
        self.name = name
        self.count = count
        self.time = time
        self.own_time = own_time
        self.parent = parent

    def accumulate(self, time: float) -> None:
        self.time += time
        self.own_time += time
        self.count += 1

    def merge(self, other: Record) -> None:
        self.time += other.time
        self.own_time += other.time
        self.count += other.count

    def copy(self) -> Record:
        return Record(self.name, self.count, self.time, self.own_time)


class Timer(ContextDecorator):
    def __init__(self, stream_on_exit: Optional = None):
        self.active_watches = []  # type: List[StopWatch]
        self.records = {}  # type: Dict[Tuple[str, ...], Record]
        self.current_name = "root"
        self.stream_on_exit = stream_on_exit

    def __call__(self, name: str = "") -> Timer:
        if name:
            self.current_name = name
        return self

    def __enter__(self) -> Timer:
        self._push()
        return self

    def __exit__(self, *exc) -> None:
        self._pop()

    def __del__(self) -> None:
        if self.stream_on_exit:
            self.stream_on_exit.write(self.render())

    @property
    def _current(self) -> Optional[StopWatch]:
        return self.active_watches[-1] if self.active_watches else None

    @property
    def _current_key(self) -> Tuple[str, ...]:
        path = [t.name for t in self.active_watches]
        return tuple(path)

    @property
    def root_records(self) -> List[Record]:
        return [r for r in self.records.values() if not r.parent]

    def frozen(self) -> Timer:
        copied = self.copy()
        while copied.active_watches:
            copied._pop()
        return copied

    def flatten(self) -> Timer:
        t = Timer(None)
        for k, v in self.records.items():
            if k[-1] in t.records:
                t.records[k[-1]].merge(v)
            else:
                t.records[k[-1]] = v.copy()

        return t

    def copy(self) -> Timer:
        t = Timer(None)
        t.records = copy.deepcopy(self.records)
        t.active_watches = copy.deepcopy(self.active_watches)
        return t

    def _push(self) -> None:
        before_push = self.records.get(self._current_key)
        self.active_watches.append(StopWatch(self.current_name))

        if self._current_key not in self.records:
            self.records[self._current_key] = Record(self._current_key[-1])
        self.records[self._current_key].parent = before_push

    def _pop(self) -> None:
        self._current.stop()
        elapsed = self._current.elapsed

        self.records[self._current_key].accumulate(elapsed)

        self.active_watches.pop()

        if self.active_watches:
            self.records[self._current_key].own_time -= elapsed

    def render(self) -> str:
        rendered = []

        for root in self.root_records:
            for pre, _, node in RenderTree(root):
                rendered.append([pre + node.name, node.count, node.time, node.own_time])
        return tabulate(rendered, headers=["path", "count", "time", "own time"])
