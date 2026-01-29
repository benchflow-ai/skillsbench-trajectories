import sys

import atheris
from IPython.core.inputtransformer2 import TransformerManager


MANAGER = TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(512)
    if not cell:
        return
    try:
        MANAGER.transform_cell(cell)
        MANAGER.check_complete(cell)
    except (SyntaxError, ValueError, RuntimeError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
