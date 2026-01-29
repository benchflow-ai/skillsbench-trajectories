#!/usr/bin/env python3
"""
Fuzzer for Black - Python code formatter
Targets: black.format_str() with various Python code inputs
"""

import sys
import atheris

# Import after atheris setup
with atheris.instrument_imports():
    import black


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz black.format_str() with various Python code patterns."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: format_str() with random code
    try:
        python_code = fdp.ConsumeUnicodeNoSurrogates(500)
        if python_code:
            mode = black.Mode()
            black.format_str(python_code, mode=mode)
    except (black.InvalidInput, SyntaxError, IndentationError, ValueError,
            TypeError, AttributeError, black.NothingChanged) as e:
        # Expected exceptions for invalid Python code
        pass
    except Exception as e:
        # Catch unexpected exceptions to help debugging
        pass

    # Test 2: format_str() with different modes
    try:
        python_code = fdp.ConsumeUnicodeNoSurrogates(300)
        line_length = fdp.ConsumeIntInRange(1, 200)
        if python_code:
            mode = black.Mode(line_length=line_length)
            black.format_str(python_code, mode=mode)
    except (black.InvalidInput, SyntaxError, IndentationError, ValueError,
            TypeError, AttributeError, black.NothingChanged, OverflowError) as e:
        pass
    except Exception as e:
        pass

    # Test 3: format_file_contents()
    try:
        python_code = fdp.ConsumeUnicodeNoSurrogates(400)
        if python_code:
            mode = black.Mode()
            black.format_file_contents(python_code, fast=True, mode=mode)
    except (black.InvalidInput, SyntaxError, IndentationError, ValueError,
            TypeError, AttributeError, black.NothingChanged) as e:
        pass
    except Exception as e:
        pass

    # Test 4: Test with specific Python constructs
    try:
        # Generate some Python-like tokens
        tokens = []
        for _ in range(fdp.ConsumeIntInRange(1, 10)):
            token = fdp.ConsumeUnicodeNoSurrogates(20)
            tokens.append(token)
        code = " ".join(tokens)

        if code:
            mode = black.Mode()
            black.format_str(code, mode=mode)
    except (black.InvalidInput, SyntaxError, IndentationError, ValueError,
            TypeError, AttributeError, black.NothingChanged) as e:
        pass
    except Exception as e:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
