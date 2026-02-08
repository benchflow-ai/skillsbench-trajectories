"""Coverage-guided fuzz driver for the Black Python code formatter."""

import sys
import atheris
from tokenize import TokenError


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Black's formatting functions."""
    import black
    import black.parsing
    from black import Mode, TargetVersion, InvalidInput

    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 2)
    src_contents = fdp.ConsumeUnicode(fdp.remaining_bytes())

    if not src_contents:
        return

    if choice == 0:
        # Fuzz black.format_str() with default mode
        mode = Mode()
        try:
            result = black.format_str(src_contents, mode=mode)
        except (InvalidInput, black.parsing.InvalidInput,
                IndentationError, SyntaxError, ValueError,
                TokenError, AssertionError):
            pass
        except Exception as e:
            # Catch known internal errors but not crashes
            error_type = type(e).__name__
            if error_type in ("NothingChanged", "CannotTransform",
                              "StringParserSyntaxError", "InvalidInput"):
                pass
            else:
                raise

    elif choice == 1:
        # Fuzz with different target versions
        mode = Mode(target_versions={TargetVersion.PY310})
        try:
            black.format_str(src_contents, mode=mode)
        except (InvalidInput, IndentationError, SyntaxError,
                ValueError, TokenError, AssertionError):
            pass
        except Exception as e:
            error_type = type(e).__name__
            if error_type in ("NothingChanged", "CannotTransform",
                              "StringParserSyntaxError", "InvalidInput"):
                pass
            else:
                raise

    elif choice == 2:
        # Fuzz black.format_str() with preview mode
        mode = Mode(preview=True)
        try:
            black.format_str(src_contents, mode=mode)
        except (InvalidInput, IndentationError, SyntaxError,
                ValueError, TokenError, AssertionError):
            pass
        except Exception as e:
            error_type = type(e).__name__
            if error_type in ("NothingChanged", "CannotTransform",
                              "StringParserSyntaxError", "InvalidInput"):
                pass
            else:
                raise


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
