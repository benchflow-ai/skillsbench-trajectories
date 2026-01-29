import sys
import tokenize
import atheris

with atheris.instrument_imports():
    import black


MODE = black.Mode()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    try:
        black.decode_bytes(data, MODE)
    except (ValueError, UnicodeError, tokenize.TokenError):
        pass
    except Exception:
        pass

    text = fdp.ConsumeUnicodeNoSurrogates(2000)
    if not text:
        return

    try:
        black.format_str(text, mode=MODE)
    except (black.InvalidInput, SyntaxError, ValueError, tokenize.TokenError):
        pass
    except Exception:
        pass

    try:
        black.format_file_contents(text, fast=True, mode=MODE)
    except (black.NothingChanged, black.InvalidInput, SyntaxError, ValueError, tokenize.TokenError):
        pass
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
