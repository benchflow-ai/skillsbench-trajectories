import os
import sys

import atheris

sys.path.insert(0, os.path.dirname(__file__))

from IPython.core.completer import CompletionSplitter
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring


@magic_arguments()
@argument("-n", "--number", type=int, default=0)
@argument("arg", nargs="?", default="")
def magic_test(self, arg):
    return arg


@magics_class
class DummyMagics(Magics):
    @line_magic
    def dummy(self, line):
        return line


TRANSFORMER = TransformerManager()
SPLITTER = CompletionSplitter()
MAGICS = DummyMagics(shell=None)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(800)

    try:
        TRANSFORMER.transform_cell(text)
        TRANSFORMER.check_complete(text)
    except Exception:
        pass

    try:
        cursor = fdp.ConsumeIntInRange(0, len(text)) if text else 0
        SPLITTER.split_line(text, cursor_pos=cursor)
    except Exception:
        pass

    try:
        parse_argstring(magic_test, text)
    except Exception:
        pass

    try:
        opt_str = "ab:c::"
        MAGICS.parse_options(text, opt_str, "long", "long2=")
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
