import os
import sys
import atheris

# minisgl uses a src layout without a package __init__.py; add python/ to path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

with atheris.instrument_imports():
    from minisgl.utils.registry import Registry
    from minisgl.utils import misc


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    reg = Registry("item")
    name1 = fdp.ConsumeUnicodeNoSurrogates(30)
    name2 = fdp.ConsumeUnicodeNoSurrogates(30)

    if name1:
        try:
            reg.register(name1)(lambda: None)
        except Exception:
            pass

    if name2:
        try:
            reg.register(name2)(lambda: None)
        except Exception:
            pass

    if name1 or name2:
        try:
            reg[fdp.PickValueInList([name1, name2, "missing"])]
        except KeyError:
            pass
        except Exception:
            pass

    try:
        reg.supported_names()
    except Exception:
        pass

    a = fdp.ConsumeIntInRange(-1000, 1000)
    b = fdp.ConsumeIntInRange(-1000, 1000)

    try:
        misc.divide_up(a, b)
    except Exception:
        pass

    try:
        misc.divide_down(a, b)
    except Exception:
        pass

    try:
        misc.divide_even(a, b)
    except Exception:
        pass

    try:
        decorator = misc.call_if_main(
            name=fdp.PickValueInList(["__main__", "not_main"]),
            discard=fdp.ConsumeBool(),
        )

        @decorator
        def _noop():
            return True

        _noop
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
