import os
import sys

import atheris

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from minisgl.utils import misc, registry  # noqa: E402


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeIntInRange(-1000, 1000)
    b = fdp.ConsumeIntInRange(1, 1000)
    if fdp.ConsumeBool():
        b = -b

    try:
        _ = misc.divide_up(a, b)
    except Exception:
        pass

    try:
        _ = misc.divide_down(a, b)
    except Exception:
        pass

    try:
        divisible = a - (a % b)
        _ = misc.divide_even(divisible, b)
    except Exception:
        pass

    try:
        name = fdp.ConsumeUnicodeNoSurrogates(16) or "__main__"
        discard = fdp.ConsumeBool()
        decorator = misc.call_if_main(name=name, discard=discard)
        _ = decorator(lambda: True)
    except Exception:
        pass

    try:
        reg = registry.Registry("thing")
        key1 = fdp.ConsumeUnicodeNoSurrogates(16)
        if key1:
            reg.register(key1)(object())
            _ = reg[key1]
        key2 = fdp.ConsumeUnicodeNoSurrogates(16)
        _ = reg.supported_names()
        try:
            _ = reg[key2]
        except Exception:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
