import atheris
import sys

from IPython.core import splitinput
from IPython.core.inputtransformer2 import TransformerManager


TRANSFORMER = TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    length = fdp.ConsumeIntInRange(0, 4096)
    cell = fdp.ConsumeUnicodeNoSurrogates(length)

    try:
        TRANSFORMER.transform_cell(cell)
    except SyntaxError:
        pass

    try:
        TRANSFORMER.check_complete(cell)
    except SyntaxError:
        pass

    try:
        splitinput.split_user_input(cell)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
