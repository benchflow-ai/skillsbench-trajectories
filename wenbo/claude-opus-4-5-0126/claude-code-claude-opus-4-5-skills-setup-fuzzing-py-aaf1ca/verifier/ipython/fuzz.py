#!/usr/bin/env python3
"""
Fuzz driver for IPython using Atheris (LibFuzzer-based).
Targets the high-priority input transformation and parsing functions
identified in notes_for_testing.txt.
"""

import sys
import atheris


def setup_imports():
    """Import target modules with instrumentation."""
    with atheris.instrument_imports():
        from IPython.core.inputtransformer2 import TransformerManager
        from IPython.core.splitinput import split_user_input, LineInfo
        from IPython.utils.tokenutil import token_at_cursor, line_at_cursor
    return TransformerManager, split_user_input, LineInfo, token_at_cursor, line_at_cursor


# Import modules with instrumentation
TransformerManager, split_user_input, LineInfo, token_at_cursor, line_at_cursor = setup_imports()


@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzz entry point targeting IPython's input transformation and parsing functions.

    Priority targets:
    1. TransformerManager.transform_cell() - Main input transformation
    2. TransformerManager.check_complete() - Completeness checking
    3. split_user_input() - Line parsing
    4. token_at_cursor() - Token extraction
    5. line_at_cursor() - Line extraction
    """
    fdp = atheris.FuzzedDataProvider(data)

    # Get input string from fuzzer
    try:
        input_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
    except Exception:
        return

    if not input_string:
        return

    # Create a transformer manager instance
    try:
        tm = TransformerManager()
    except Exception:
        return

    # Test 1: TransformerManager.transform_cell() - Main transformation entry point
    try:
        tm.transform_cell(input_string)
    except (ValueError, TypeError, SyntaxError, IndentationError, RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test 2: TransformerManager.check_complete() - Completeness checking
    try:
        tm.check_complete(input_string)
    except (ValueError, TypeError, SyntaxError, IndentationError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: split_user_input() - Line parsing with regex
    try:
        split_user_input(input_string)
    except (ValueError, TypeError, RecursionError):
        pass
    except Exception:
        pass

    # Test 4: LineInfo class - Line information parsing
    try:
        LineInfo(input_string)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 5: token_at_cursor() - Token extraction at various cursor positions
    try:
        cursor_pos = fdp.ConsumeIntInRange(0, len(input_string) + 10)
        token_at_cursor(input_string, cursor_pos)
    except (ValueError, TypeError, IndexError):
        pass
    except Exception:
        pass

    # Test 6: line_at_cursor() - Line extraction at cursor position
    try:
        cursor_pos = fdp.ConsumeIntInRange(0, len(input_string) + 10)
        line_at_cursor(input_string, cursor_pos)
    except (ValueError, TypeError, IndexError):
        pass
    except Exception:
        pass

    # Test 7: Test with IPython-specific syntax patterns
    # Add common IPython escape sequences to test
    escape_patterns = ['%', '%%', '!', '!!', '?', '??', '/', ',', ';']
    try:
        escape_choice = fdp.ConsumeIntInRange(0, len(escape_patterns) - 1)
        escaped_input = escape_patterns[escape_choice] + input_string
        tm.transform_cell(escaped_input)
    except (ValueError, TypeError, SyntaxError, IndentationError, RecursionError):
        pass
    except Exception:
        pass

    # Test 8: Multi-line input transformation
    try:
        lines = input_string.split('\n')
        if lines:
            for line in lines[:10]:  # Limit to avoid excessive processing
                tm.transform_cell(line)
    except (ValueError, TypeError, SyntaxError, IndentationError, RecursionError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
