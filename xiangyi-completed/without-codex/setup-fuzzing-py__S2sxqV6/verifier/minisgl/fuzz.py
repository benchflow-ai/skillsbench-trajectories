import sys

import atheris

with atheris.instrument_imports():
    from minisgl import env
    from minisgl.utils import misc


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    mem_str = fdp.ConsumeUnicodeNoSurrogates(32)
    if mem_str:
        try:
            env._PARSE_MEM_BYTES(mem_str)
        except (ValueError, KeyError):
            pass

    a = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    b = fdp.ConsumeIntInRange(1, 1_000_000)
    try:
        misc.divide_even(a, b)
    except (AssertionError, ZeroDivisionError):
        pass

    misc.divide_up(a, b)
    misc.divide_down(a, b)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
