"""Coverage-guided fuzz driver for the IPython library."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for IPython input transformation and parsing."""
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))

    if not text:
        return

    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input

    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz TransformerManager.transform_cell()
            tm = TransformerManager()
            tm.transform_cell(text)
        elif choice == 1:
            # Fuzz TransformerManager.check_complete()
            tm = TransformerManager()
            tm.check_complete(text)
        elif choice == 2:
            # Fuzz split_user_input()
            for line in text.splitlines():
                split_user_input(line)
        elif choice == 3:
            # Fuzz arg_split()
            from IPython.utils._process_common import arg_split
            arg_split(text, posix=fdp.ConsumeBool())
    except (
        ValueError,
        TypeError,
        SyntaxError,
        IndentationError,
        OverflowError,
        IndexError,
        KeyError,
        AttributeError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        StopIteration,
        RecursionError,
        tokenize.TokenError,
    ):
        pass
    except Exception as e:
        err_name = type(e).__name__
        if err_name in ("TokenError", "InputRejected"):
            pass
        else:
            raise


import tokenize


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
