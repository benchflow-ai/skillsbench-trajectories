import sys

import atheris

with atheris.instrument_imports():
    from minisgl.env import _PARSE_MEM_BYTES
    from minisgl.utils.misc import divide_down, divide_even, divide_up


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    mem_str = fdp.ConsumeUnicodeNoSurrogates(32)
    a = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    b = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if b == 0:
        b = 1

    try:
        _PARSE_MEM_BYTES(mem_str)
    except (KeyError, ValueError, IndexError, TypeError):
        pass

    try:
        divide_even(a, b)
    except (AssertionError, ZeroDivisionError):
        pass

    try:
        divide_up(a, b)
        divide_down(a, b)
    except ZeroDivisionError:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
