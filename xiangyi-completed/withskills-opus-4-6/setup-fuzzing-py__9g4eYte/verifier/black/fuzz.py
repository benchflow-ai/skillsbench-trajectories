"""Coverage-guided fuzz driver for the Black code formatter using Atheris (LibFuzzer)."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Black's code formatting functions."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        from black import format_str, format_file_contents, Mode, TargetVersion
        from black.parsing import lib2to3_parse
    except ImportError:
        return

    src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))

    # Build a Mode with fuzzed options
    try:
        mode = Mode(
            line_length=fdp.ConsumeIntInRange(1, 200),
            string_normalization=fdp.ConsumeBool(),
            is_pyi=fdp.ConsumeBool(),
            magic_trailing_comma=fdp.ConsumeBool(),
        )
    except Exception:
        mode = Mode()

    # Fuzz format_str - primary formatting API
    try:
        format_str(src, mode=mode)
    except Exception:
        pass

    # Fuzz lib2to3_parse - the CST parser
    try:
        lib2to3_parse(src)
    except Exception:
        pass

    # Fuzz format_file_contents with fast=True to avoid slow safety checks
    try:
        format_file_contents(src, fast=True, mode=mode)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
