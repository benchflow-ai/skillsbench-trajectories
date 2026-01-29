import os
import sys
import atheris
import importlib.util


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE_DIR = os.path.dirname(__file__)
MISC_PATH = os.path.join(BASE_DIR, "python", "minisgl", "utils", "misc.py")
REG_PATH = os.path.join(BASE_DIR, "python", "minisgl", "utils", "registry.py")

misc = _load_module("minisgl_utils_misc", MISC_PATH)
registry = _load_module("minisgl_utils_registry", REG_PATH)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeInt(64)
    b = fdp.ConsumeInt(32) or 1
    name = fdp.ConsumeUnicodeNoSurrogates(30) or "x"

    try:
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            misc.divide_even(a, b)
            misc.divide_up(a, b)
            misc.divide_down(a, b)
        elif choice == 1:
            deco = misc.call_if_main("__main__" if fdp.ConsumeBool() else name, discard=fdp.ConsumeBool())
            deco(lambda: 123)
        elif choice == 2:
            reg = registry.Registry("item")
            reg.register(name)(object())
            reg.supported_names()
            reg[name]
        else:
            reg = registry.Registry("item")
            try:
                reg[name]
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
