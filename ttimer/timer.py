"""
MIT License

Copyright (c) 2022 nyanp

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import copy
import inspect
import os
import threading
import time
from dataclasses import asdict, dataclass
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


class TimerContext:
    def __init__(self, timer: Timer, name: str):
        self.timer = timer
        self.name = name

    def __enter__(self) -> Timer:
        self.timer._push(self.name)
        return self.timer

    def __exit__(self, *exc: Any) -> None:
        self.timer._pop()


class Timer:
    def __init__(self, stream_on_exit: Optional[Union[Logger, IO[str]]] = None):
        self._watches = []  # type: List[StopWatch]
        self._nodes = {}  # type: Dict[Tuple[str, ...], Node]
        self._stream_on_exit = stream_on_exit

    def __call__(self, name: str = "") -> TimerContext:
        return TimerContext(self, name or self._get_caller_name(2))

    def __enter__(self) -> Timer:
        self._push(self._get_caller_name(2))
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

    def clear(self) -> None:
        self._watches = []
        self._nodes = {}

    def render(self, flat: bool = False) -> str:
        rendered = []

        for pre, _, rec in self._iterate_nodes(flat):
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

    def to_dict(self, flat: bool = False) -> List[Dict[str, Any]]:
        list_of_dict = []
        for _, stack, rec in self._iterate_nodes(flat):
            d = asdict(rec)
            if not flat:
                d["stack"] = stack
            list_of_dict.append(d)
        return list_of_dict

    def _push(self, name: str) -> None:
        parent = self._nodes.get(self._stack)

        self._watches.append(StopWatch(name))
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

    def _iterate_nodes(
        self, flat: bool = False
    ) -> Generator[Tuple[str, Tuple[str, ...], Record], None, None]:
        if flat:
            for record in self.records:
                yield "", ("",), record
        else:
            for root in self.trees:
                for pre, _, node in RenderTree(root):
                    yield pre, node.stack, node.record

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


def timer(timer_name: Optional[str] = None) -> Func:
    def _timer(func: Func) -> Func:
        @wraps(func)
        def _inner(*args: Any, **kws: Any) -> Any:
            if timer_name is None:
                assert "timer" in kws, (
                    "Without specifying timer_name, "
                    "you will need to pass the timer with an extra keyword argument"
                )
                timer = kws["timer"]
                assert isinstance(timer, Timer)
                kws.pop("timer")
            else:
                timer = get_timer(timer_name)

            with timer(func.__name__):
                result = func(*args, **kws)
            return result

        return _inner

    return _timer
