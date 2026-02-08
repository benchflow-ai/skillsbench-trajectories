"""Coverage-guided fuzz driver for the IPython library."""

import sys
import atheris
from tokenize import TokenError


def TestOneInput(data: bytes) -> None:
    """Fuzz target for IPython's input transformation and parsing."""
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input, LineInfo

    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)
    input_str = fdp.ConsumeUnicode(fdp.remaining_bytes())

    if not input_str:
        return

    if choice == 0:
        # Fuzz TransformerManager.transform_cell()
        tm = TransformerManager()
        try:
            tm.transform_cell(input_str)
        except (SyntaxError, ValueError, IndexError, KeyError,
                TokenError, IndentationError, UnicodeDecodeError,
                OverflowError, RecursionError):
            pass

    elif choice == 1:
        # Fuzz TransformerManager.check_complete()
        tm = TransformerManager()
        try:
            tm.check_complete(input_str)
        except (SyntaxError, ValueError, IndexError, KeyError,
                TokenError, IndentationError, UnicodeDecodeError,
                OverflowError, RecursionError):
            pass

    elif choice == 2:
        # Fuzz split_user_input()
        try:
            split_user_input(input_str)
        except (SyntaxError, ValueError, IndexError, KeyError,
                UnicodeDecodeError):
            pass

    elif choice == 3:
        # Fuzz LineInfo()
        try:
            li = LineInfo(input_str)
            str(li)
        except (SyntaxError, ValueError, IndexError, KeyError,
                UnicodeDecodeError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
