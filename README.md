# ttimer
ttimer is a simple timer that keeps track of the call hierarchy.

## Example

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

If the name is not passed in the with-statement, it will be given automatically.

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

If you do not prefer such a thread-local variables, you can simply create a local `Timer` instance.
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
