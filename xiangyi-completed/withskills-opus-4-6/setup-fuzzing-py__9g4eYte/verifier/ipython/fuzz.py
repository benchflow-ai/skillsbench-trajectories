"""Coverage-guided fuzz driver for IPython using Atheris (LibFuzzer)."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for IPython's input processing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        from IPython.core.inputtransformer2 import TransformerManager
        from IPython.core.splitinput import split_user_input
        from IPython.utils.tokenutil import token_at_cursor
    except ImportError:
        return

    input_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))

    # Fuzz TransformerManager.transform_cell - primary input pipeline
    tm = TransformerManager()
    try:
        tm.transform_cell(input_str)
    except Exception:
        pass

    # Fuzz TransformerManager.check_complete - completeness checking
    try:
        tm.check_complete(input_str)
    except Exception:
        pass

    # Fuzz split_user_input - regex-based input decomposition
    try:
        split_user_input(input_str)
    except Exception:
        pass

    # Fuzz token_at_cursor - token identification at cursor position
    cursor_pos = fdp.ConsumeIntInRange(0, max(len(input_str), 1))
    try:
        token_at_cursor(input_str, cursor_pos)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
