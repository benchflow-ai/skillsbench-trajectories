#!/usr/bin/env python3
"""LibFuzzer harness for Black Python code formatter."""

import sys
import atheris

try:
    import black
except ImportError as e:
    print(f"Failed to import black: {e}", file=sys.stderr)
    sys.exit(1)


def fuzz_black_format_str(data: bytes) -> None:
    """Fuzz black.format_str()"""
    try:
        # Convert bytes to string
        input_str = data.decode('utf-8', errors='ignore')

        # Try to format Python code
        try:
            mode = black.FileMode()
            black.format_str(input_str, mode=mode)
        except (black.NothingChanged, SyntaxError, ValueError, TypeError):
            pass

        # Try with different line lengths
        try:
            mode = black.FileMode(line_length=80)
            black.format_str(input_str, mode=mode)
        except (black.NothingChanged, SyntaxError, ValueError, TypeError):
            pass

    except (UnicodeDecodeError, MemoryError, RuntimeError, OSError):
        pass


def fuzz_black_parsing(data: bytes) -> None:
    """Fuzz Black's internal parsing mechanisms"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Try to parse the input
        try:
            mode = black.FileMode()
            black.lib2to3_parse(input_str)
        except SyntaxError:
            pass

    except Exception:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing function."""
    fuzz_black_format_str(data)
    fuzz_black_parsing(data)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
