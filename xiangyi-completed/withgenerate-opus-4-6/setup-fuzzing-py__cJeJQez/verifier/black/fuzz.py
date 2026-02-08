"""Coverage-guided fuzz driver for the Black code formatter.

Targets:
- black.format_str() - main entry point for formatting Python source code
"""
import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import format_str, Mode, InvalidInput, NothingChanged
    from black.parsing import lib2to3_parse
    from blib2to3.pgen2.parse import ParseError
    from blib2to3.pgen2.tokenize import TokenError as Blib2to3TokenError


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    source = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not source:
        return

    mode = Mode()

    try:
        format_str(source, mode=mode)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
