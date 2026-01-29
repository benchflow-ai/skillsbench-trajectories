import os
import sys

import atheris

# Ensure the local package is importable even without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from minisgl import env as minisgl_env
from minisgl.utils import misc, registry


_MAX_TEXT = 128


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_TEXT, fdp.remaining_bytes()))

    if text:
        try:
            minisgl_env._PARSE_MEM_BYTES(text)
        except Exception:
            pass

        try:
            os.environ["MINISGL_TEST_ENV"] = text
            env_var = minisgl_env.EnvVar(0, int)
            env_var._init("MINISGL_TEST_ENV")
        except Exception:
            pass

    a = fdp.ConsumeIntInRange(-10**6, 10**6)
    b = fdp.ConsumeIntInRange(-10**6, 10**6) or 1

    try:
        misc.divide_even(a, b)
    except Exception:
        pass
    try:
        misc.divide_up(a, b)
    except Exception:
        pass
    try:
        misc.divide_down(a, b)
    except Exception:
        pass

    reg = registry.Registry("thing")
    name = fdp.ConsumeUnicodeNoSurrogates(16)
    if name:
        try:
            @reg.register(name)
            def _item():
                return None
        except Exception:
            pass
        try:
            reg.supported_names()
        except Exception:
            pass
        try:
            reg[name]
        except Exception:
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
