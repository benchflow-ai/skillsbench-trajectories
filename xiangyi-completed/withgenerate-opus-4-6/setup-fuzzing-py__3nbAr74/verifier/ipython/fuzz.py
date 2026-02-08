"""Coverage-guided fuzz driver for the IPython library."""
import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils.tokenutil import token_at_cursor, line_at_cursor
    from IPython.core.splitinput import split_user_input


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz TransformerManager.transform_cell
        cell = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            tm = TransformerManager()
            tm.transform_cell(cell)
        except (ValueError, TypeError, SyntaxError, OverflowError,
                RecursionError, IndexError, KeyError, tokenize.TokenError,
                UnicodeDecodeError, Exception):
            pass

    elif choice == 1:
        # Fuzz token_at_cursor
        cell = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        cursor_pos = fdp.ConsumeIntInRange(0, max(len(cell), 1))
        try:
            token_at_cursor(cell, cursor_pos)
        except (ValueError, TypeError, IndexError, tokenize.TokenError,
                UnicodeDecodeError, Exception):
            pass

    elif choice == 2:
        # Fuzz line_at_cursor
        cell = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        cursor_pos = fdp.ConsumeIntInRange(0, max(len(cell), 1))
        try:
            line_at_cursor(cell, cursor_pos)
        except (ValueError, TypeError, IndexError, Exception):
            pass

    else:
        # Fuzz split_user_input
        line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            split_user_input(line)
        except (ValueError, TypeError, IndexError, Exception):
            pass


import tokenize


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
