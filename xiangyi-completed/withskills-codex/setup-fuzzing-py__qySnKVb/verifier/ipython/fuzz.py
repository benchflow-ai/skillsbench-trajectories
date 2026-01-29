import sys
import tokenize
from io import StringIO

import atheris

with atheris.instrument_imports():
    from IPython.core import inputtransformer2
    from IPython.core import splitinput
    from IPython.utils import tokenutil
    from IPython.utils import text as textutil


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(400)

    tm = inputtransformer2.TransformerManager()
    try:
        _ = tm.transform_cell(cell)
        _ = tm.check_complete(cell)
    except Exception:
        # Let unexpected exceptions surface
        raise

    try:
        _ = splitinput.split_user_input(cell)
    except Exception:
        raise

    try:
        list(tokenutil.generate_tokens_catch_errors(StringIO(cell).readline))
    except tokenize.TokenError:
        # Expected for malformed inputs.
        return

    try:
        _ = textutil.strip_email_quotes(cell)
        _ = textutil.dedent(cell)
        _ = textutil.indent(cell, nspaces=fdp.ConsumeIntInRange(0, 8))
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
