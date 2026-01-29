import sys

import atheris

with atheris.instrument_imports():
    from IPython.core import splitinput
    from IPython.core.inputtransformer2 import TransformerManager


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        cell = fdp.ConsumeUnicodeNoSurrogates(400)
        tm = TransformerManager()
        try:
            tm.transform_cell(cell)
        except Exception:
            pass
        try:
            tm.check_complete(cell)
        except Exception:
            pass
        line = fdp.ConsumeUnicodeNoSurrogates(200)
        try:
            splitinput.split_user_input(line)
        except Exception:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
