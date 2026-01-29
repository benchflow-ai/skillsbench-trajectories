#!/usr/bin/env python3
"""IPython library fuzzer using Atheris"""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz IPython's input transformation"""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Generate fuzzed cell code
        cell_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 5000))

        # Create a transformer manager instance
        transformer = TransformerManager()

        # Test transform_cell
        try:
            transformed = transformer.transform_cell(cell_code)
        except (SyntaxError, ValueError, AttributeError):
            # Expected exceptions for malformed code
            pass

        # Test check_complete
        try:
            result = transformer.check_complete(cell_code)
        except (SyntaxError, ValueError, AttributeError):
            # Expected exceptions
            pass

        # Test with various inputs
        if len(data) > 10:
            # Test with magic commands
            magic_cell = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 200))
            try:
                magic_transformed = transformer.transform_cell(magic_cell)
            except (SyntaxError, ValueError, AttributeError):
                pass

            # Test check_complete with different code patterns
            try:
                complete_result = transformer.check_complete(magic_cell)
            except (SyntaxError, ValueError, AttributeError):
                pass

    except Exception:
        # Catch any unexpected exceptions and report them
        raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
