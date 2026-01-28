import sys
import os
import atheris

# Ensure local package path
sys.path.append(os.path.join(os.path.dirname(__file__), "python"))

from minisgl.utils import misc
from minisgl import env as envmod


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeIntInRange(-10**6, 10**6)
    b = fdp.ConsumeIntInRange(-10**6, 10**6)
    if b == 0:
        b = 1
    try:
        misc.divide_up(a, b)
    except Exception:
        pass
    try:
        misc.divide_even(a, b)
    except Exception:
        pass
    s = fdp.ConsumeUnicodeNoSurrogates(50)
    try:
        envmod._PARSE_MEM_BYTES(s)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
