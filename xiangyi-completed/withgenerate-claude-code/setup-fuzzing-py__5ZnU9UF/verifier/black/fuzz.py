#!/usr/bin/env python3
"""
Fuzz driver for Black - Python code formatter
Focuses on format_str() which is the main formatting function
"""
import sys
import atheris

# Import after atheris for better instrumentation
with atheris.instrument_imports():
    import black
    from black import InvalidInput, NothingChanged


def TestOneInput(data):
    """Fuzz black.format_str() with Python code"""
    fdp = atheris.FuzzedDataProvider(data)

    # Generate Python-like code to format
    code = fdp.ConsumeUnicodeNoSurrogates(1000)

    try:
        # Try to format the code
        # Use default mode
        formatted = black.format_str(code, mode=black.Mode())
    except (InvalidInput, NothingChanged, ValueError, TypeError, TokenError, IndentationError):
        # Expected exceptions for invalid or unparseable Python code
        pass
    except SyntaxError:
        # Also expected for invalid syntax
        pass
    except RecursionError:
        # Can happen with deeply nested code - acceptable
        pass

    # Test 2: Format with different line lengths
    if fdp.remaining_bytes() > 100:
        code = fdp.ConsumeUnicodeNoSurrogates(500)
        line_length = fdp.ConsumeIntInRange(1, 200)
        try:
            mode = black.Mode(line_length=line_length)
            formatted = black.format_str(code, mode=mode)
        except (InvalidInput, NothingChanged, ValueError, TypeError, TokenError, IndentationError, SyntaxError, RecursionError):
            pass


# Import TokenError if it exists (it's from tokenize module)
from tokenize import TokenError


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
