import os
import sys

import atheris

from minisgl import env as minisgl_env


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    mem_text = fdp.ConsumeUnicodeNoSurrogates(16)
    bool_text = fdp.ConsumeUnicodeNoSurrogates(8)
    env_name = "MINISGL_FUZZ_" + fdp.ConsumeUnicodeNoSurrogates(8)

    if mem_text and mem_text.strip():
        try:
            minisgl_env._PARSE_MEM_BYTES(mem_text)
        except (ValueError, KeyError, OverflowError):
            pass

    try:
        minisgl_env._TO_BOOL(bool_text)
    except Exception:
        pass

    # Exercise EnvVar parsing path with a temp env var
    prev = os.environ.get(env_name)
    try:
        os.environ[env_name] = mem_text
        ev = minisgl_env.EnvVar(0, int)
        ev._init(env_name)
        bool(ev)
        str(ev)
    except Exception:
        pass
    finally:
        if prev is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = prev


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
