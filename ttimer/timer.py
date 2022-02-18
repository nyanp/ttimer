from __future__ import annotations

import copy
import inspect
import os
import time
from contextlib import ContextDecorator
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from anytree import NodeMixin, RenderTree
from tabulate import tabulate


class StopWatch:
    def __init__(self, name: str):
        self.name = name
        self.start = (time.perf_counter(), time.process_time())
        self.elapsed_time = 0.0
        self.elapsed_cpu_time = 0.0

    def stop(self) -> None:
        self.elapsed_time = time.perf_counter() - self.start[0]
        self.elapsed_cpu_time = time.process_time() - self.start[1]


@dataclass
class Record:
    name: str
    count: int = 0
    time: float = 0.0
    own_time: float = 0.0
    cpu_time: float = 0.0
    own_cpu_time: float = 0.0

    def on_stop(self, stop_watch: StopWatch) -> None:
        self.time += stop_watch.elapsed_time
        self.own_time += stop_watch.elapsed_time
        self.cpu_time += stop_watch.elapsed_cpu_time
        self.own_cpu_time += stop_watch.elapsed_cpu_time
        self.count += 1

    def on_stop_child(self, stop_watch: StopWatch) -> None:
        self.own_time -= stop_watch.elapsed_time
        self.own_cpu_time -= stop_watch.elapsed_cpu_time

    def merge(self, other: Record) -> None:
        self.time += other.time
        self.own_time += other.own_time
        self.cpu_time += other.cpu_time
        self.own_cpu_time += other.own_cpu_time
        self.count += other.count


class Node(NodeMixin):
    def __init__(self, record: Record, parent: Optional[Node] = None):
        super().__init__()
        self.record = record
        self.parent = parent


class Timer(ContextDecorator):
    def __init__(self, stream_on_exit: Optional = None):
        self._watches = []  # type: List[StopWatch]
        self._records = {}  # type: Dict[Tuple[str, ...], Node]
        self._current_name = ""
        self._stream_on_exit = stream_on_exit

    def __call__(self, name: str = "") -> Timer:
        self._current_name = name
        return self

    def __enter__(self) -> Timer:
        if not self._current_name:
            self._current_name = self._get_caller_name(2)
        self._push()
        return self

    def __exit__(self, *exc) -> None:
        self._pop()

    def __del__(self) -> None:
        if self._stream_on_exit:
            self._stream_on_exit.write(self.render())

    def __getitem__(self, item: str) -> Record:
        candidates = [r for k, r in self._records.items() if k[-1] == item]
        if not candidates:
            raise KeyError(f"{item} not found")
        record = copy.copy(candidates[0].record)
        for c in candidates[1:]:
            record.merge(c.record)
        return record

    @property
    def trees(self) -> List[Node]:
        return [r for r in self._records.values() if not r.parent]

    def render(self) -> str:
        rendered = []

        for root in self.trees:
            for pre, _, node in RenderTree(root):
                rec = node.record
                rendered.append(
                    [
                        pre + rec.name,
                        rec.count,
                        rec.time,
                        rec.own_time,
                        rec.cpu_time,
                        rec.own_cpu_time,
                    ]
                )

        return tabulate(
            rendered,
            headers=["path", "count", "time", "own time", "cpu time", "own cpu time"],
        )

    def _push(self) -> None:
        parent = self._records.get(self._stack)

        self._watches.append(StopWatch(self._current_name))
        if self._stack not in self._records:
            self._records[self._stack] = Node(Record(self._stack[-1]), parent=parent)

    def _pop(self) -> None:
        self._current_watch.stop()

        self._current_node.record.on_stop(self._current_watch)
        if self._current_node.parent:
            self._current_node.parent.record.on_stop_child(self._current_watch)

        self._watches.pop()
        self._current_name = self._stack[-1] if self._stack else ""

    @property
    def _current_node(self) -> Node:
        return self._records[self._stack]

    @property
    def _current_watch(self) -> StopWatch:
        assert self._watches
        return self._watches[-1]

    @property
    def _stack(self) -> Tuple[str, ...]:
        return tuple([t.name for t in self._watches])

    def _get_caller_name(self, index: int) -> str:
        try:
            callee = inspect.stack()[index]
            return f"{os.path.basename(callee.filename)}:{callee.lineno}"
        except Exception:
            return "(unknown)"
