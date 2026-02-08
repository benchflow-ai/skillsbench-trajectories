import atheris
import sys
import tokenize

# Import heavy transitive dependencies BEFORE atheris.instrument_imports()
# to avoid instrumenting hundreds of unrelated modules (traitlets, prompt_toolkit,
# pygments, jedi, parso, etc.) which causes very slow startup.
import traitlets  # noqa: F401
import pygments  # noqa: F401
import jedi  # noqa: F401
import parso  # noqa: F401
import prompt_toolkit  # noqa: F401

# Only instrument the specific IPython modules we are fuzzing
with atheris.instrument_imports():
    from IPython.core import inputtransformer2
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core import splitinput
    from IPython.core.splitinput import split_user_input
    from IPython.utils import tokenutil
    from IPython.utils.tokenutil import token_at_cursor

tm = TransformerManager()


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    fuzz_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 4096))
    cursor_pos = fdp.ConsumeIntInRange(0, len(fuzz_string))

    try:
        tm.transform_cell(fuzz_string)
    except (SyntaxError, ValueError, TypeError, tokenize.TokenError, IndentationError):
        pass

    try:
        tm.check_complete(fuzz_string)
    except (SyntaxError, ValueError, TypeError, tokenize.TokenError, IndentationError):
        pass

    try:
        split_user_input(fuzz_string)
    except (SyntaxError, ValueError, TypeError, tokenize.TokenError, IndentationError):
        pass

    try:
        token_at_cursor(fuzz_string, cursor_pos)
    except (SyntaxError, ValueError, TypeError, tokenize.TokenError, IndentationError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
