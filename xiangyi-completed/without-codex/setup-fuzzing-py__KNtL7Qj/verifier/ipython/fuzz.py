import sys
import tokenize
import atheris

with atheris.instrument_imports():
    from IPython.core import inputtransformer2
    from IPython.core import splitinput
    from IPython.utils import text as ipy_text
    from IPython.core.magic_arguments import magic_arguments, argument, parse_argstring


@magic_arguments()
@argument("name", nargs="*")
def _dummy_magic(line):
    return line


TRANSFORMER = inputtransformer2.TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(2000)
    if not cell:
        return

    try:
        TRANSFORMER.transform_cell(cell)
    except (SyntaxError, tokenize.TokenError, RuntimeError, ValueError):
        pass
    except Exception:
        pass

    try:
        TRANSFORMER.check_complete(cell)
    except (SyntaxError, tokenize.TokenError, RuntimeError, ValueError):
        pass
    except Exception:
        pass

    try:
        splitinput.split_user_input(cell)
    except Exception:
        pass

    try:
        ipy_text.strip_email_quotes(cell)
    except Exception:
        pass

    try:
        ipy_text.format_screen(cell)
    except Exception:
        pass

    try:
        parse_argstring(_dummy_magic, cell)
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
