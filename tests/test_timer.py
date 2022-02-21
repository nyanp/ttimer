import time

from ttimer.timer import Timer, get_timer, timer


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


def test_count():
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
    assert t["b"].count == 2
    assert t["c"].count == 1


def test_nodes():
    t = Timer()

    with t("a"):
        with t("b"):
            with t("c"):
                pass

            with t("d"):
                pass

        with t("d"):
            pass

    assert len(t.nodes) == 5
    assert t.nodes[0].stack == ("a",)
    assert t.nodes[0].children[0].stack == ("a", "b")
    assert t.nodes[0].children[1].stack == ("a", "d")
    assert t.nodes[0].children[0].children[0].stack == ("a", "b", "c")
    assert t.nodes[0].children[0].children[1].stack == ("a", "b", "d")


def test_records():
    t = Timer()

    with t("a"):
        with t("b"):
            with t("c"):
                pass

            with t("d"):
                pass

        with t("d"):
            pass

    assert len(t.records) == 4
    assert t.records[0].name == "a"
    assert t.records[1].name == "b"
    assert t.records[2].name == "c"
    assert t.records[3].name == "d"


def test_auto_name():
    t = Timer()

    with t("b"):
        pass

    with t:
        pass

    with t():
        pass

    assert t.nodes[0].record.name == "b"
    assert t.nodes[1].record.name.startswith("test_auto_name(test_timer.py:")
    assert t.nodes[2].record.name.startswith("test_auto_name(test_timer.py:")
    assert t.nodes[1].record.name != t.nodes[2].record.name


def test_auto_name_nested():
    t = Timer()

    with t():
        with t("b"):
            pass

        with t:
            pass

        with t():
            pass

    assert len(set([n.record.name for n in t.nodes])) == 4


@timer("abc")
def func(a: int) -> None:
    pass


def test_decorator():
    t1 = get_timer("abc")
    t2 = get_timer("def")

    with t2:
        func(2)

    assert t1["func"].count == 1


@timer()
def func2(a: int) -> None:
    pass


def test_decorator_with_local_timer():
    timer = Timer()

    with timer("foo"):
        func2(2, timer=timer)
        func2(2, timer=timer)

    assert len(timer.records) == 2
    assert timer["func2"].count == 2


def test_to_dict():
    t = Timer()

    with t("a"):
        time.sleep(0.1)

        for _ in range(10):
            with t("b"):
                time.sleep(0.01)

    with t("b"):
        time.sleep(0.1)

    d = t.to_dict(flat=False)
    assert len(d) == 3
    assert d[0]["name"] == "a"
    assert d[0]["count"] == 1
    assert d[0]["stack"] == ("a",)
    assert d[1]["name"] == "b"
    assert d[1]["count"] == 10
    assert d[1]["stack"] == ("a", "b")
    assert d[2]["name"] == "b"
    assert d[2]["count"] == 1
    assert d[2]["stack"] == ("b",)

    d = t.to_dict(flat=True)
    assert len(d) == 2
    assert d[0]["name"] == "a"
    assert d[0]["count"] == 1
    assert d[1]["name"] == "b"
    assert d[1]["count"] == 11


def test_render():
    t = Timer()

    with t("a"):
        time.sleep(0.1)

        for _ in range(10):
            with t("b"):
                time.sleep(0.01)

    with t("b"):
        time.sleep(0.1)

    print(t.render())
    print(t.render(flat=True))
