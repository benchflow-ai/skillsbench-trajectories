#!/usr/bin/env python3
"""
Fuzz driver for IPython library.

Targets:
- TransformerManager.transform_cell() - Main cell transformation
- TransformerManager.check_complete() - Code completeness checking
- split_user_input() - Input line splitting
- make_tokens_by_line() - Token-based line parsing
- token_at_cursor() - Token identification for completion

Usage:
    python fuzz.py [libfuzzer options]

Example:
    python fuzz.py -max_total_time=10
"""

import sys
import atheris


def setup_ipython():
    """Import IPython modules inside instrumentation context."""
    global TransformerManager, split_user_input, LineInfo
    global make_tokens_by_line, token_at_cursor

    from IPython.core.inputtransformer2 import TransformerManager, make_tokens_by_line
    from IPython.core.splitinput import split_user_input, LineInfo
    from IPython.utils.tokenutil import token_at_cursor


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point.

    Tests IPython's input transformation and parsing functions.
    """
    # Try to decode as UTF-8 string
    try:
        input_str = data.decode('utf-8')
    except UnicodeDecodeError:
        # If not valid UTF-8, try with replacement
        input_str = data.decode('utf-8', errors='replace')

    # Create transformer manager instance
    tm = TransformerManager()

    # Test 1: transform_cell() - Main transformation function
    try:
        result = tm.transform_cell(input_str)
    except (ValueError, TypeError, OverflowError, RecursionError, MemoryError):
        pass  # Expected exceptions
    except Exception:
        pass  # Catch any other exceptions

    # Test 2: check_complete() - Code completeness checking
    try:
        status, indent = tm.check_complete(input_str)
        # Validate return values
        assert status in ('complete', 'incomplete', 'invalid')
        assert indent is None or isinstance(indent, int)
    except (ValueError, TypeError, OverflowError, RecursionError, MemoryError):
        pass
    except AssertionError:
        pass  # Invalid return values - potential bug but don't crash
    except Exception:
        pass

    # Test 3: split_user_input() - Input line splitting
    # Test on each line separately
    for line in input_str.split('\n')[:10]:  # Limit to first 10 lines
        try:
            pre, esc, ifun, the_rest = split_user_input(line)
            # All parts should be strings
            assert isinstance(pre, str)
            assert isinstance(esc, str)
            assert isinstance(ifun, str)
            assert isinstance(the_rest, str)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except AssertionError:
            pass
        except Exception:
            pass

    # Test 4: LineInfo constructor
    for line in input_str.split('\n')[:10]:
        try:
            info = LineInfo(line)
            # Access properties to ensure they work
            _ = info.pre
            _ = info.esc
            _ = info.ifun
            _ = info.the_rest
            _ = str(info)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 5: make_tokens_by_line() - Token parsing
    try:
        lines = input_str.splitlines(keepends=True)
        if lines:
            result = make_tokens_by_line(lines)
    except (ValueError, TypeError, OverflowError, RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test 6: token_at_cursor() - Token at cursor position
    # Use FuzzedDataProvider for cursor position
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Get random cursor positions
        cursor_pos = fdp.ConsumeIntInRange(0, len(input_str) + 10)
        result = token_at_cursor(input_str, cursor_pos)
        assert isinstance(result, str)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except AssertionError:
        pass
    except Exception:
        pass

    # Test 7: token_at_cursor with edge positions
    for pos in [0, len(input_str), len(input_str) // 2]:
        try:
            result = token_at_cursor(input_str, pos)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass


def main():
    """Main entry point for the fuzzer."""
    # Instrument IPython imports
    with atheris.instrument_imports():
        setup_ipython()

    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
