import sys

import atheris
from IPython.core import inputtransformer2, magic_arguments, splitinput
from IPython.core import completer as ipy_completer


_MAX_TEXT = 4096

_TRANSFORMER = inputtransformer2.TransformerManager()
_COMPLETER = ipy_completer.Completer()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_TEXT, fdp.remaining_bytes()))

    if text:
        try:
            _TRANSFORMER.transform_cell(text)
        except Exception:
            pass
        try:
            _TRANSFORMER.check_complete(text)
        except Exception:
            pass
        try:
            splitinput.split_user_input(text)
        except Exception:
            pass
        try:
            magic_arguments.parse_argstring(lambda: None, text)
        except Exception:
            pass
        try:
            cursor = fdp.ConsumeIntInRange(0, len(text))
            _COMPLETER.split_line(text, cursor)
        except Exception:
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
