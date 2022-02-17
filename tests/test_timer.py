import time

import pytest

from ttimer.timer import Timer


def test_nested():
    t = Timer()

    with t("a"):
        time.sleep(0.1)

        for _ in range(10):
            with t("b"):
                time.sleep(0.01)

    assert t["a"].count == 1
    assert t["a"].own_time >= 0.1
    assert t["a"].time >= 0.2
    assert t["a"].time > t["a"].own_time + 0.1

    assert t["b"].count == 10
    assert t["b"].own_time > 0.1
    assert t["b"].own_time == t["b"].time
    assert t["b"].cpu_time == t["b"].own_cpu_time


def test_tree():
    t = Timer()

    with t("a"):
        time.sleep(0.1)
        with t("b"):
            time.sleep(0.01)
        with t("c"):
            time.sleep(0.01)

    with t("b"):
        time.sleep(0.01)

    assert t["a"].count == 1
    with pytest.raises(KeyError):
        print(t["b"].count)
    assert t[("a", "b")].count == 1
    assert t[("b",)].count == 1
    assert t["c"].count == 1


def test_render():
    t = Timer()

    with t("a"):
        time.sleep(0.1)

        for _ in range(10):
            with t("b"):
                time.sleep(0.01)

    print(t.render())
