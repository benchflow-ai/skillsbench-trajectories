import sys
import tokenize
import atheris
from IPython.core.inputtransformer2 import TransformerManager


_TRANSFORMER = TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(400)
    try:
        _TRANSFORMER.transform_cell(src)
    except (SyntaxError, ValueError, IndentationError, tokenize.TokenError):
        return


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
