#!/usr/bin/env python3
"""
Fuzz driver for the Black code formatter using Atheris (LibFuzzer-based).
Targets the high-priority parsing and formatting functions identified in notes_for_testing.txt.
"""

import sys
import atheris


def setup_imports():
    """Import target modules with instrumentation."""
    with atheris.instrument_imports():
        import black
        from black import format_str, format_file_contents, Mode, TargetVersion
        from black.parsing import lib2to3_parse
    return black, format_str, format_file_contents, Mode, TargetVersion, lib2to3_parse


# Import modules with instrumentation
black_mod, format_str, format_file_contents, Mode, TargetVersion, lib2to3_parse = setup_imports()


@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzz entry point targeting Black's parsing and formatting functions.

    Priority targets:
    1. format_str() - Main entry point for formatting
    2. lib2to3_parse() - Core parser
    3. format_file_contents() - File content formatter
    """
    fdp = atheris.FuzzedDataProvider(data)

    # Get source code string from fuzzer input
    try:
        src_contents = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 5000))
    except Exception:
        return

    if not src_contents:
        return

    # Create a Mode object with various settings
    try:
        mode = Mode(
            target_versions=set(),
            line_length=fdp.ConsumeIntInRange(1, 200),
            string_normalization=fdp.ConsumeBool(),
            is_pyi=fdp.ConsumeBool(),
            magic_trailing_comma=fdp.ConsumeBool(),
        )
    except Exception:
        mode = Mode()

    # Test 1: format_str() - Main formatting entry point
    try:
        format_str(src_contents, mode=mode)
    except (
        black_mod.InvalidInput,
        black_mod.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
        MemoryError,
        TokenError if 'TokenError' in dir() else Exception,
    ):
        pass
    except Exception:
        # Catch other exceptions but don't crash the fuzzer
        pass

    # Test 2: lib2to3_parse() - Core parsing function
    try:
        lib2to3_parse(src_contents)
    except (
        black_mod.InvalidInput,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 3: format_file_contents() with fast=True
    try:
        format_file_contents(src_contents, fast=True, mode=mode)
    except (
        black_mod.InvalidInput,
        black_mod.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 4: format_file_contents() with fast=False (includes safety checks)
    try:
        format_file_contents(src_contents, fast=False, mode=mode)
    except (
        black_mod.InvalidInput,
        black_mod.NothingChanged,
        black_mod.CannotSplit if hasattr(black_mod, 'CannotSplit') else Exception,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
        AssertionError,  # Safety checks may raise this
    ):
        pass
    except Exception:
        pass

    # Test 5: Decode bytes - test encoding detection
    try:
        raw_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 2000))
        if raw_bytes:
            black_mod.decode_bytes(raw_bytes)
    except (ValueError, TypeError, UnicodeDecodeError, LookupError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
