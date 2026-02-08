import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.parsing import InvalidInput, ASTSafetyError
    from black.report import NothingChanged
    from blib2to3.pgen2.tokenize import TokenError as Blib2to3TokenError
    from tokenize import TokenError


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    if not src:
        return

    mode = black.Mode()

    # Target 1: black.format_str()
    try:
        black.format_str(src, mode=mode)
    except (
        InvalidInput,
        NothingChanged,
        IndentationError,
        SyntaxError,
        TokenError,
        Blib2to3TokenError,
        ValueError,
    ):
        pass

    # Target 2: black.format_file_contents()
    try:
        black.format_file_contents(src, fast=False, mode=mode)
    except (
        InvalidInput,
        NothingChanged,
        ASTSafetyError,
        IndentationError,
        SyntaxError,
        TokenError,
        Blib2to3TokenError,
        ValueError,
    ):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
