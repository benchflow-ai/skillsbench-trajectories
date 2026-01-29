import atheris
import sys
import importlib.machinery
import importlib.util
from pathlib import Path


_MISC_PATH = Path(__file__).parent / "python" / "minisgl" / "utils" / "misc.py"

spec = importlib.util.spec_from_loader(
    "minisgl_utils_misc", importlib.machinery.SourceFileLoader("minisgl_utils_misc", str(_MISC_PATH))
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeIntInRange(-10_000, 10_000)
    b = fdp.ConsumeIntInRange(-10_000, 10_000)
    if b == 0:
        b = 1

    try:
        module.divide_up(a, b)
        module.divide_down(a, b)
        if a % b == 0:
            module.divide_even(a, b)
    except (AssertionError, ZeroDivisionError, OverflowError):
        pass

    name_len = fdp.ConsumeIntInRange(0, 32)
    name = fdp.ConsumeUnicodeNoSurrogates(name_len)
    try:
        decorator = module.call_if_main(name, discard=fdp.ConsumeBool())
        def _dummy():
            return True
        decorator(_dummy)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
