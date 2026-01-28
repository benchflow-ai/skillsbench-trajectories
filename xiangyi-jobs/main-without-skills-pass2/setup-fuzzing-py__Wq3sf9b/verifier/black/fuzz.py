import sys
import atheris
import black
from black import FileMode


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(400)
    mode = FileMode()

    try:
        black.format_str(src, mode=mode)
    except (black.InvalidInput, SyntaxError, ValueError):
        pass

    try:
        black.format_file_contents(src, fast=True, mode=mode)
    except (black.NothingChanged, black.InvalidInput, SyntaxError, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
