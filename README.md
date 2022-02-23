# ttimer
ttimer is a simple timer that keeps track of the call hierarchy.
ttimer is intended to fulfill a use case somewhere between a timer and a profiler: 
like a timer, it measures only where you explicitly write it, while like a profiler, it handles the call hierarchy and measures own time.

## Usage

```python
>>> from time import sleep
>>> from ttimer import get_timer

>>> timer = get_timer(timer_name="my timer")

>>> with timer("a"):
>>>     sleep(0.1)
>>>     for _ in range(10):
>>>         with timer("b"):
>>>             sleep(0.01)
>>> with timer("b"):
>>>     sleep(0.1)

>>> print(timer.render())

path      count      time    own time    cpu time    own cpu time
------  -------  --------  ----------  ----------  --------------
a             1  0.203831    0.100531    0.001314        0.000784
└── b        10  0.103299    0.103299    0.00053         0.00053
b             1  0.103603    0.103603    8.2e-05         8.2e-05

>>> print(timer.render(flat=True))

path      count      time    own time    cpu time    own cpu time
------  -------  --------  ----------  ----------  --------------
a             1  0.203831    0.100531    0.001314        0.000784
b            11  0.206903    0.206903    0.000612        0.000612

```

ttimer records the following metrics in the with-statement:

- **count**: Call count.
- **time**: Elapsed time measured by [`perf_counter`](https://docs.python.org/3.10/library/time.html?highlight=time%20perf_counter#time.perf_counter). It includes time elapsed during sleep and is system-wide.
- **own time**: Time, excluding the total time of its children.
- **cpu time**: CPU time measured by [`process_time`](https://docs.python.org/3.10/library/time.html?highlight=time%20perf_counter#time.process_time).
- **own cpu time**: Process time, excluding the total time of its children.

If the name is not passed in the with-statement, 
the name will be automatically assigned from the file and function names.

```python
>>> from ttimer import get_timer

>>> t = get_timer("foo")
>>> with t:
>>>     pass

>>> print(t.render())
path                                  count         time     own time    cpu time    own cpu time
----------------------------------  -------  -----------  -----------  ----------  --------------
test_get_timers(test_timer.py:144)        1  0.000347945  0.000347945    0.000228        0.000228
```

You can also use decorators instead of with-statement:

```python
from ttimer import timer

@timer(timer_name="my timer")
def foo(a: int):
    pass
```

In either usage, timers with the same `timer_name` share the same elapsed time.
This is useful when you want to measure times across modules.

All named timers are stored as a thread-local variable,
and you can use `get_timers` to enumerate the stored timers.

```python
>>> from ttimer import get_timer, get_timers

>>> with get_timer("foo"):
>>>    pass
>>> with get_timer("bar"):
>>>     pass

>>> all_timers = get_timers()
{'foo': <ttimer.timer.Timer object at 0x7fc9a334fc50>, 'bar': <ttimer.timer.Timer object at 0x7fc9a334df98>}
```

### Local timers

If you do not prefer global (thread-local) variables, you can simply create a local `Timer` instance.
In this style, if you use a decorator, you should pass the timer you created as an additional `timer` keyword argument.

```python
from ttimer import Timer, timer

t = Timer()  # local timer

@timer()
def foo(a: int):
    pass

with t("a"):
    foo(a=1, timer=t)  # additional "timer" keyword argument are used to specify the context
```

### Properties
By accessing `timer[key]`, you can get the accumulated result as an instance of `Record` dataclass.
You can of course also get a list of records by `.records`.

```python
from dataclasses import asdict
from ttimer import get_timer

timer = get_timer("my timer")

with timer("a"):
    pass

print("result of {}:".format(timer["a"].name))
print("time:         {}".format(timer["a"].time))
print("cpu time:     {}".format(timer["a"].cpu_time))
print("own time:     {}".format(timer["a"].own_time))
print("own cpu time: {}".format(timer["a"].own_cpu_time))
print("count:        {}".format(timer["a"].count))

print(asdict(timer["a"]))  # result is dataclass

timer.records  # list of records
```

The results you can get with above are equivalent to `flat=True`: i.e., the measurements with the same name are accumulated.
If you want to get the measurements for each call stack separately, you can use `.nodes`.

`.nodes` returns all the nodes, but if you want to get only the root node, use `.trees`. 
Both return an instance of `Node`, and you can access the child nodes with `.children`, or access the node's records with `.record`.

```python
from ttimer import get_timer, Record

timer = get_timer("my timer")

with timer("a"):
    with timer("b"):
        pass
    
with timer("b"):
    pass

assert len(timer.records) == 2
assert len(timer.nodes) == 3
assert timer.nodes[1].stack == ("a", "b")
assert isinstance(timer.nodes[1].record, Record)
assert len(timer.trees) == 2
```
