#!/usr/bin/env python3
"""Black library fuzzer using Atheris"""

import atheris
import sys

with atheris.instrument_imports():
    import black

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz Black's format_str function"""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Generate fuzzed Python code
        source_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 5000))

        # Test format_str with default mode
        try:
            result = black.format_str(source_code, mode=black.FileMode())
        except (black.InvalidInput, ValueError, SyntaxError):
            # Expected exceptions for malformed code
            pass

        # Test with different line lengths
        if len(data) > 5:
            line_length = fdp.ConsumeIntInRange(10, 200)
            try:
                mode = black.FileMode(line_length=line_length)
                result = black.format_str(source_code, mode=mode)
            except (black.InvalidInput, ValueError, SyntaxError):
                # Expected exceptions
                pass

        # Test string normalization option
        if len(data) > 10:
            normalize = fdp.ConsumeBool()
            try:
                mode = black.FileMode(string_normalization=normalize)
                result = black.format_str(source_code, mode=mode)
            except (black.InvalidInput, ValueError, SyntaxError):
                # Expected exceptions
                pass

    except Exception:
        # Catch any unexpected exceptions and report them
        raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
