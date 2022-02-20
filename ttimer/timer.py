from __future__ import annotations

import copy
import inspect
import os
import threading
import time
from dataclasses import dataclass
from functools import wraps
from logging import Logger
from typing import IO, Any, Callable, Dict, Generator, List, Optional, Tuple, Union

from anytree import NodeMixin, RenderTree
from tabulate import tabulate

Func = Callable[..., Any]


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


class Node(NodeMixin):  # type: ignore
    def __init__(
        self, stack: Tuple[str, ...], record: Record, parent: Optional[Node] = None
    ):
        super().__init__()
        self.stack = stack
        self.record = record
        self.parent = parent


class Timer:
    def __init__(self, stream_on_exit: Optional[Union[Logger, IO[str]]] = None):
        self._watches = []  # type: List[StopWatch]
        self._nodes = {}  # type: Dict[Tuple[str, ...], Node]
        self._current_name = ""
        self._stream_on_exit = stream_on_exit

    def __call__(self, name: str = "") -> Timer:  # type: ignore
        self._current_name = name
        return self

    def __enter__(self) -> Timer:
        if not self._current_name:
            self._current_name = self._get_caller_name(2)
        self._push()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._pop()

    def __del__(self) -> None:
        if self._stream_on_exit:
            if isinstance(self._stream_on_exit, Logger):
                self._stream_on_exit.info(self.render())
            else:
                self._stream_on_exit.write(self.render())

    def __getitem__(self, item: str) -> Record:
        candidates = [r for k, r in self._nodes.items() if k[-1] == item]
        if not candidates:
            raise KeyError(f"{item} not found")
        record = copy.copy(candidates[0].record)
        for c in candidates[1:]:
            record.merge(c.record)
        return record

    @property
    def trees(self) -> List[Node]:
        return [n for n in self.nodes if not n.parent]

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    @property
    def records(self) -> List[Record]:
        return [self[k] for k in {k[-1]: None for k in self._nodes.keys()}.keys()]

    def render(self, flat: bool = False) -> str:
        rendered = []

        for pre, rec in self._iterate_nodes(flat):
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
        parent = self._nodes.get(self._stack)

        self._watches.append(StopWatch(self._current_name))
        if self._stack not in self._nodes:
            self._nodes[self._stack] = Node(
                self._stack, Record(self._stack[-1]), parent=parent
            )

    def _pop(self) -> None:
        self._current_watch.stop()

        self._current_node.record.on_stop(self._current_watch)
        if self._current_node.parent:
            self._current_node.parent.record.on_stop_child(self._current_watch)

        self._watches.pop()
        self._current_name = self._stack[-1] if self._stack else ""

    def _iterate_nodes(
        self, flat: bool = False
    ) -> Generator[Tuple[str, Record], None, None]:
        if flat:
            for record in self.records:
                yield "", record
        else:
            for root in self.trees:
                for pre, _, node in RenderTree(root):
                    yield pre, node.record

    @property
    def _current_node(self) -> Node:
        return self._nodes[self._stack]

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
            return f"{callee.function}({os.path.basename(callee.filename)}:{callee.lineno})"
        except Exception:
            return "(unknown)"


_thread_local = threading.local()


def get_timer(timer_name: str) -> Timer:
    if not getattr(_thread_local, "timers", None):
        _thread_local.timers = {}

    if timer_name not in _thread_local.timers:
        _thread_local.timers[timer_name] = Timer()

    return _thread_local.timers[timer_name]  # type: ignore


def get_timers() -> Dict[str, Timer]:
    return _thread_local.timers  # type: ignore


def timer(timer_name: str) -> Func:
    def _timer(func: Func) -> Func:
        @wraps(func)
        def _inner(*args: Any, **kws: Any) -> Any:
            with get_timer(timer_name)(func.__name__):
                result = func(*args, **kws)
            return result

        return _inner

    return _timer
