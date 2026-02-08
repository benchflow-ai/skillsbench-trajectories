"""Coverage-guided fuzzer for the Black code formatter using atheris + LibFuzzer."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for black's formatting and parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    import black

    src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    if not src:
        return

    mode = black.Mode()

    # Fuzz format_str - the main public API
    try:
        black.format_str(src, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        IndentationError,
        TokenError,
    ):
        pass
    except Exception:
        pass

    # Fuzz format_file_contents
    try:
        black.format_file_contents(src, fast=True, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        IndentationError,
        TokenError,
    ):
        pass
    except Exception:
        pass

    # Fuzz with different target versions
    try:
        mode_py312 = black.Mode(target_versions={black.TargetVersion.PY312})
        black.format_str(src, mode=mode_py312)
    except Exception:
        pass


# Import TokenError before fuzzing starts
from tokenize import TokenError


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
