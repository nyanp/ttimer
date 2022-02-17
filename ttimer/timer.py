from __future__ import annotations

import copy
import time
from contextlib import ContextDecorator
from dataclasses import replace
from typing import Dict, List, Optional, Tuple, Union

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


class Record(NodeMixin):
    def __init__(self,
                 name: str,
                 count: int = 0,
                 time: float = 0.0,
                 own_time: float = 0.0,
                 cpu_time: float = 0.0,
                 own_cpu_time: float = 0.0,
                 parent: Optional[Record] = None):
        super().__init__()
        self.name = name
        self.count = count
        self.time = time
        self.cpu_time = cpu_time
        self.own_time = own_time
        self.own_cpu_time = own_cpu_time
        self.parent = parent

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

    def copy(self) -> Record:
        return replace(self, parent=None)


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

    def __getitem__(self, item: Union[str, Tuple[str, ...]]) -> Record:
        if isinstance(item, tuple):
            return self.records[item]
        else:
            candidates = [r for k, r in self.records.items() if k[-1] == item]
            if len(candidates) >= 2:
                raise KeyError(f"The name {item} is ambiguous. Call flatten() before, or use full path")
            elif len(candidates) == 1:
                return candidates[0]
            else:
                raise KeyError(f"{item} not found")

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

    def render(self) -> str:
        rendered = []

        for root in self.root_records:
            for pre, _, node in RenderTree(root):
                rendered.append(
                    [pre + node.name, node.count, node.time, node.own_time, node.cpu_time, node.own_cpu_time])

        return tabulate(rendered, headers=["path", "count", "time", "own time", "cpu time", "own cpu time"])

    def _push(self) -> None:
        parent = self.records.get(self._current_key)

        self.active_watches.append(StopWatch(self.current_name))
        if self._current_key not in self.records:
            self.records[self._current_key] = Record(self._current_key[-1], parent=parent)

    def _pop(self) -> None:
        self._current_watch.stop()

        self._current_record.on_stop(self._current_watch)
        if self._current_record.parent:
            self._current_record.parent.on_stop_child(self._current_watch)

        self.active_watches.pop()

    @property
    def _current_record(self) -> Record:
        return self.records[self._current_key]

    @property
    def _current_watch(self) -> StopWatch:
        assert self.active_watches
        return self.active_watches[-1]

    @property
    def _current_key(self) -> Tuple[str, ...]:
        path = [t.name for t in self.active_watches]
        return tuple(path)
