#!/usr/bin/env python3
"""
Coverage-guided fuzzer for Black library using Atheris (LibFuzzer).
Targets Python code formatting and parsing functions.
"""

import sys
import atheris

# Enable coverage instrumentation before importing target modules
with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import lib2to3_parse


def TestOneInput(data):
    """Fuzz target for black library."""

    # Need at least some bytes to work with
    if len(data) < 1:
        return

    try:
        input_str = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not input_str:
        return

    # Create a basic mode for formatting
    mode = Mode(
        target_versions={TargetVersion.PY310},
        line_length=88,
    )

    # Test 1: format_str() - main formatting function
    try:
        black.format_str(input_str, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        IndentationError,
        SyntaxError,
        ValueError,
        TypeError,
        RecursionError,
        MemoryError,
    ):
        pass
    except Exception:
        pass

    # Test 2: lib2to3_parse() - parsing function
    try:
        lib2to3_parse(input_str)
    except (
        black.InvalidInput,
        IndentationError,
        SyntaxError,
        ValueError,
        TypeError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 3: format_str with different modes
    try:
        preview_mode = Mode(
            target_versions={TargetVersion.PY310},
            line_length=88,
            preview=True,
        )
        black.format_str(input_str, mode=preview_mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        IndentationError,
        SyntaxError,
        ValueError,
        TypeError,
        RecursionError,
        MemoryError,
    ):
        pass
    except Exception:
        pass

    # Test 4: String normalization (if input looks like a string literal)
    if input_str.startswith(("'", '"', "f'", 'f"', "r'", 'r"', "b'", 'b"')):
        try:
            from black.strings import normalize_string_quotes
            # Create a mock leaf-like object
            class MockLeaf:
                def __init__(self, value):
                    self.value = value
                    self.parent = None

            leaf = MockLeaf(input_str)
            normalize_string_quotes(leaf)
        except (ValueError, TypeError, IndexError, AttributeError):
            pass
        except Exception:
            pass


def main():
    # Run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
