import sys

import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager


_MANAGER = TransformerManager()


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(2000)

    try:
        _MANAGER.transform_cell(cell)
    except (SyntaxError, RuntimeError, ValueError):
        pass

    try:
        _MANAGER.check_complete(cell)
    except (SyntaxError, RuntimeError, ValueError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
