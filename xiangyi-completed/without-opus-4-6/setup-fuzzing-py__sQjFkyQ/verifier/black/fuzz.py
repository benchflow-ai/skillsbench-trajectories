import sys
import atheris


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    import black

    # Fuzz black.format_str() - the main entry point
    try:
        black.format_str(src, mode=black.Mode())
    except (
        black.InvalidInput,
        black.NothingChanged,
        IndentationError,
        SyntaxError,
        ValueError,
        TypeError,
        AssertionError,
        RecursionError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        TokenError,
    ):
        pass
    except Exception:
        pass


def main():
    # Import TokenError at module level for the except clause
    global TokenError
    from tokenize import TokenError

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
