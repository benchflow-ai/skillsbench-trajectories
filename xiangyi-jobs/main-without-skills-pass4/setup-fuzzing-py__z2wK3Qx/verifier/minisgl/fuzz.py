import sys

import atheris

with atheris.instrument_imports():
    from minisgl.utils import misc
    from minisgl.utils.registry import Registry


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    reg = Registry("item")
    name1 = fdp.ConsumeUnicodeNoSurrogates(24)
    name2 = fdp.ConsumeUnicodeNoSurrogates(24)

    if name1:
        try:
            @reg.register(name1)
            def _item():
                return name1
        except KeyError:
            pass

    try:
        reg[name2]
    except Exception:
        pass

    reg.supported_names()

    a = fdp.ConsumeIntInRange(-10**6, 10**6)
    b = fdp.ConsumeIntInRange(-10**6, 10**6)
    if b == 0:
        b = 1

    try:
        misc.divide_up(a, b)
        misc.divide_down(a, b)
        if a % b == 0:
            misc.divide_even(a, b)
    except Exception:
        pass

    name = fdp.ConsumeUnicodeNoSurrogates(24) or "__main__"
    decorator = misc.call_if_main(name, discard=fdp.ConsumeBool())
    try:
        def _f():
            return True
        decorator(_f)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
