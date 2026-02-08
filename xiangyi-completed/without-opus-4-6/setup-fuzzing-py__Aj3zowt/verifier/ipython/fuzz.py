"""Coverage-guided fuzzer for IPython's input parsing using atheris + LibFuzzer."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for IPython's input parsing and transformation functions."""
    fdp = atheris.FuzzedDataProvider(data)

    from IPython.core.splitinput import split_user_input, LineInfo
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils.tokenutil import token_at_cursor, line_at_cursor

    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    if not text:
        return

    # Fuzz split_user_input
    try:
        split_user_input(text)
    except Exception:
        pass

    # Fuzz LineInfo
    try:
        LineInfo(text)
    except Exception:
        pass

    # Fuzz TransformerManager.transform_cell
    tm = TransformerManager()
    try:
        tm.transform_cell(text)
    except Exception:
        pass

    # Fuzz TransformerManager.check_complete
    try:
        tm.check_complete(text)
    except Exception:
        pass

    # Fuzz token_at_cursor
    cursor_pos = fdp.ConsumeIntInRange(0, len(text) + 1)
    try:
        token_at_cursor(text, cursor_pos)
    except Exception:
        pass

    # Fuzz line_at_cursor
    try:
        line_at_cursor(text, cursor_pos)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
