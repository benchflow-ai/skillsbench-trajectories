#!/usr/bin/python3
"""Coverage-guided fuzz driver for the Black Python code formatter.

Targets:
  1. black.format_str()         - Main formatting API
  2. black.decode_bytes()       - Byte decoding with encoding detection
  3. lib2to3_parse()            - Python source code parsing (CST)
"""
import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.mode import Mode, TargetVersion
    from black.parsing import lib2to3_parse, InvalidInput
    from black.report import NothingChanged

# Import TokenError used by blib2to3
try:
    from blib2to3.pgen2.tokenize import TokenError
except ImportError:
    TokenError = Exception

# Reusable mode instances
_default_mode = Mode()


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    if fdp.remaining_bytes() < 2:
        return
    target = fdp.ConsumeIntInRange(0, 2)

    if target == 0:
        # Target 1: format_str - main public API
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            black.format_str(src, mode=_default_mode)
        except (InvalidInput, IndentationError, TokenError, AssertionError,
                ValueError, RecursionError):
            pass

    elif target == 1:
        # Target 2: decode_bytes - raw bytes decoding
        raw = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            content, encoding, newline = black.decode_bytes(raw, _default_mode)
        except (SyntaxError, UnicodeDecodeError, LookupError, ValueError):
            pass

    elif target == 2:
        # Target 3: lib2to3_parse - Python source parsing
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            lib2to3_parse(src)
        except (InvalidInput, RecursionError, TokenError, IndentationError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
