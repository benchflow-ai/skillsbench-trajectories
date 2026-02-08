import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.splitinput import split_user_input, LineInfo
    from IPython.utils.text import strip_email_quotes, dedent, EvalFormatter
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    # Fuzz split_user_input
    try:
        split_user_input(text)
    except (ValueError, TypeError, IndexError, AttributeError):
        pass

    # Fuzz LineInfo
    try:
        li = LineInfo(text)
    except (ValueError, TypeError, IndexError, AttributeError):
        pass

    # Fuzz strip_email_quotes
    try:
        strip_email_quotes(text)
    except (ValueError, TypeError, IndexError):
        pass

    # Fuzz dedent
    try:
        dedent(text)
    except (ValueError, TypeError, IndexError):
        pass

    # Fuzz TransformerManager.transform_cell
    try:
        tm = TransformerManager()
        tm.transform_cell(text)
    except (ValueError, TypeError, IndexError, SyntaxError, TokenError, KeyError,
            AttributeError, RecursionError, IndentationError, UnicodeDecodeError):
        pass


from tokenize import TokenError

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
