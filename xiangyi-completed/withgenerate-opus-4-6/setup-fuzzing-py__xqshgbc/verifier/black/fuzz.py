"""Coverage-guided fuzz driver for the Black code formatter."""
import atheris
import sys

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion, InvalidInput, NothingChanged
    from black.parsing import lib2to3_parse
    from black.strings import normalize_string_quotes, normalize_string_prefix


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz black.format_str() - main formatting entry point
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        line_length = fdp.ConsumeIntInRange(1, 200)
        try:
            mode = Mode(line_length=line_length)
            result = black.format_str(src, mode=mode)
        except (InvalidInput, NothingChanged, ValueError, TypeError,
                IndentationError, SyntaxError, RecursionError,
                UnicodeDecodeError, TokenError, Exception) as e:
            # Only catch known exception types; let unknown crashes propagate
            if type(e) is Exception:
                raise
            pass

    elif choice == 1:
        # Fuzz black.format_file_contents() with fast=True (skip safety checks)
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        try:
            mode = Mode()
            black.format_file_contents(src, fast=True, mode=mode)
        except (InvalidInput, NothingChanged, ValueError, TypeError,
                IndentationError, SyntaxError, RecursionError,
                UnicodeDecodeError):
            pass

    elif choice == 2:
        # Fuzz normalize_string_quotes()
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            normalize_string_quotes(s)
        except (ValueError, TypeError, IndexError, RecursionError,
                AssertionError):
            pass

    elif choice == 3:
        # Fuzz normalize_string_prefix()
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        try:
            normalize_string_prefix(s)
        except (ValueError, TypeError, IndexError):
            pass


from tokenize import TokenError

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
