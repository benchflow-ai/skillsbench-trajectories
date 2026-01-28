import sys
import tokenize

import atheris
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input


TRANSFORMER = TransformerManager()


def _consume_text(fdp, max_len: int) -> str:
    return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, max_len))


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    cell = _consume_text(fdp, 2000)

    try:
        TRANSFORMER.transform_cell(cell)
    except (SyntaxError, tokenize.TokenError, ValueError, RuntimeError):
        pass

    try:
        TRANSFORMER.check_complete(cell)
    except (SyntaxError, tokenize.TokenError, ValueError):
        pass

    try:
        split_user_input(cell)
    except (SyntaxError, ValueError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
