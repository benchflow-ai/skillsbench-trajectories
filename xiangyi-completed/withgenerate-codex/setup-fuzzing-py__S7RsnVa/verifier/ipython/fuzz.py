import sys
import tokenize

import atheris

from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(400)
    line = fdp.ConsumeUnicodeNoSurrogates(200)

    it = TransformerManager()

    try:
        it.transform_cell(cell)
    except (SyntaxError, tokenize.TokenError, ValueError):
        pass

    try:
        it.check_complete(cell)
    except (SyntaxError, tokenize.TokenError, ValueError):
        pass

    try:
        split_user_input(line)
    except (SyntaxError, ValueError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
