import sys
import atheris


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    if not s:
        return

    try:
        black.format_str(s, mode=mode)
    except black.parsing.InvalidInput:
        pass
    except (
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        OverflowError,
        KeyError,
        IndexError,
        AttributeError,
        RecursionError,
        UnicodeEncodeError,
        UnicodeDecodeError,
        RuntimeError,
        AssertionError,
        TokenError,
    ):
        pass


def main():
    atheris.instrument_all()
    global black, mode, TokenError
    import black as _black
    import black.parsing
    from tokenize import TokenError as _TokenError
    from black import Mode
    black = _black
    mode = Mode()
    TokenError = _TokenError
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
