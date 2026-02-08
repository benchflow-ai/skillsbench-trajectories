"""Coverage-guided fuzz driver for the Black code formatter."""

import sys
import atheris
from tokenize import TokenError


def TestOneInput(data: bytes):
    """Fuzz target for black code formatting functions."""
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))

    if not src.strip():
        return

    from black import format_str, Mode, InvalidInput
    from black.parsing import lib2to3_parse

    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz format_str - main public API
            mode = Mode()
            format_str(src, mode=mode)
        elif choice == 1:
            # Fuzz format_str with different line lengths
            line_length = fdp.ConsumeIntInRange(1, 200)
            mode = Mode(line_length=line_length)
            format_str(src, mode=mode)
        elif choice == 2:
            # Fuzz lib2to3_parse directly
            lib2to3_parse(src)
    except (
        InvalidInput,
        SyntaxError,
        ValueError,
        TypeError,
        IndentationError,
        TokenError,
        AttributeError,
        IndexError,
        AssertionError,
    ):
        pass
    except Exception as e:
        err_name = type(e).__name__
        if err_name in (
            "InvalidInput",
            "NothingChanged",
            "CannotSplit",
            "StringParenthesisStripError",
        ):
            pass
        else:
            raise


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
