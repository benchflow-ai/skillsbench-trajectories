"""Coverage-guided fuzzer for the Black Python code formatter."""

import sys
import atheris


def TestOneInput(data):
    """Fuzz target for Black's formatting functions."""
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    if not src:
        return

    import black
    from black.mode import Mode, TargetVersion

    mode = Mode(
        target_versions={TargetVersion.PY311},
        line_length=88,
    )

    # Fuzz format_str - the main entry point
    try:
        black.format_str(src, mode=mode)
    except black.InvalidInput:
        pass
    except black.NothingChanged:
        pass
    except Exception:
        pass

    # Fuzz with fast mode (skips AST equivalence check)
    try:
        black.format_file_contents(src, fast=True, mode=mode)
    except black.NothingChanged:
        pass
    except Exception:
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
