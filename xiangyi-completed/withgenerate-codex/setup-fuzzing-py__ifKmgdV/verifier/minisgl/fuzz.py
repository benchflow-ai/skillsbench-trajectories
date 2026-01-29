import os
import sys

import atheris
from atheris import FuzzedDataProvider

ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ROOT, "python"))

from minisgl.utils import misc
from minisgl.utils.registry import Registry


def TestOneInput(data: bytes) -> None:
    fdp = FuzzedDataProvider(data)

    a = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    b = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if b == 0:
        b = 1

    try:
        misc.divide_even(a, b)
    except AssertionError:
        pass

    misc.divide_up(a, b)
    misc.divide_down(a, b)

    # Registry behavior
    reg = Registry("widget")
    name1 = fdp.ConsumeUnicodeNoSurrogates(16)
    name2 = fdp.ConsumeUnicodeNoSurrogates(16)

    def _item():
        return 1

    try:
        reg.register(name1)(_item)
    except KeyError:
        pass
    try:
        reg.register(name2)(_item)
    except KeyError:
        pass

    try:
        reg[name1]
    except KeyError:
        pass
    try:
        reg[name2]
    except KeyError:
        pass

    reg.supported_names()

    # call_if_main behavior
    name = fdp.ConsumeUnicodeNoSurrogates(16)
    decorator = misc.call_if_main(name=name, discard=fdp.ConsumeBool())

    def _noop():
        return True

    try:
        decorator(_noop)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
