import sys

import atheris
from atheris import FuzzedDataProvider

from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input
from IPython.core.magic_arguments import MagicArgumentParser, UsageError
from IPython.core.magic import Magics, magics_class


@magics_class
class _DummyMagic(Magics):
    pass


def TestOneInput(data: bytes) -> None:
    fdp = FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(512)

    # Input transformers
    tm = TransformerManager()
    try:
        tm.transform_cell(text)
    except (SyntaxError, RuntimeError, ValueError):
        pass

    try:
        tm.check_complete(text)
    except (SyntaxError, ValueError):
        pass

    # Split user input
    try:
        split_user_input(text)
    except Exception:
        pass

    # Magic argument parsing
    parser = MagicArgumentParser("dummy", add_help=False)
    try:
        parser.parse_argstring(text, partial=False)
    except (UsageError, ValueError):
        pass
    except SystemExit:
        pass

    # Options parsing (getopt-style)
    try:
        dummy = _DummyMagic(shell=None)
    except Exception:
        dummy = None
    opt_str = fdp.ConsumeUnicodeNoSurrogates(8)
    long_opts = []
    for _ in range(fdp.ConsumeIntInRange(0, 2)):
        long_opts.append(fdp.ConsumeUnicodeNoSurrogates(10))
    if dummy is not None:
        try:
            dummy.parse_options(text, opt_str, *long_opts)
        except Exception:
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
