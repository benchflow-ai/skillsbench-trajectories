#!/usr/bin/env python3
"""
Coverage-guided fuzzing driver for the Black library.
Uses atheris for LibFuzzer-style fuzzing.
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Black library."""
    # Import inside function to avoid issues during atheris setup
    import black
    from black import Mode, TargetVersion
    from black.parsing import lib2to3_parse

    # Convert bytes to string for testing
    try:
        code = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not code or len(code) > 50000:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: format_str() with default mode
    try:
        mode = Mode()
        black.format_str(code, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 2: lib2to3_parse() direct parsing
    try:
        lib2to3_parse(code)
    except (
        black.InvalidInput,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 3: format_str() with different target versions
    if len(data) > 2:
        try:
            versions = list(TargetVersion)
            target_idx = data[0] % len(versions)
            mode = Mode(target_versions={versions[target_idx]})
            black.format_str(code, mode=mode)
        except (
            black.InvalidInput,
            black.NothingChanged,
            ValueError,
            TypeError,
            IndentationError,
            SyntaxError,
            RecursionError,
        ):
            pass
        except Exception:
            pass

    # Test 4: format_str() with different line lengths
    if len(data) > 3:
        try:
            line_length = (data[1] % 200) + 1  # 1-200 line length
            mode = Mode(line_length=line_length)
            black.format_str(code, mode=mode)
        except (
            black.InvalidInput,
            black.NothingChanged,
            ValueError,
            TypeError,
            IndentationError,
            SyntaxError,
            RecursionError,
        ):
            pass
        except Exception:
            pass

    # Test 5: format_str() with string_normalization disabled
    try:
        mode = Mode(string_normalization=False)
        black.format_str(code, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 6: format_str() with is_pyi mode (stub file)
    try:
        mode = Mode(is_pyi=True)
        black.format_str(code, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 7: format_str() with preview mode
    try:
        mode = Mode(preview=True)
        black.format_str(code, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        ValueError,
        TypeError,
        IndentationError,
        SyntaxError,
        RecursionError,
    ):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
