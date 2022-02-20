# ttimer
ttimer is a simple timer that keeps track of the calling hierarchy.

## Example

```python
>>> from time import sleep
>>> from ttimer import Timer

>>> timer = Timer()

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

To accumulate time on the same timer across modules, you can use named timers.
Named timers are simply thread-local dictionary.
Timers in the same thread and with the same name share the same instance.

```python
from ttimer import get_timer

timer = get_timer(timer_name="module 1")  # named timer

with timer("a"):
    pass
```

Named timers can also be used as decorators.

```python
from ttimer import timer

@timer(timer_name="module 1")
def foo():
    pass
```