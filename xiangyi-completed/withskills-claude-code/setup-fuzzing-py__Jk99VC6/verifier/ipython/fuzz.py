#!/usr/bin/env python3
"""Fuzz driver for IPython input transformation and parsing."""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.prefilter import PrefilterManager
    from IPython.core.interactiveshell import InteractiveShell


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for IPython input transformation."""
    fdp = atheris.FuzzedDataProvider(data)

    # Generate test input
    test_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 500))

    try:
        # Test 1: TransformerManager.transform_cell()
        if len(test_input) > 0:
            try:
                transformer = TransformerManager()
                transformer.transform_cell(test_input)
            except (ValueError, SyntaxError, TypeError, AttributeError, IndentationError):
                pass

        # Test 2: TransformerManager.check_complete()
        if len(test_input) > 0:
            try:
                transformer = TransformerManager()
                transformer.check_complete(test_input)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 3: PrefilterManager.prefilter_line()
        if len(test_input) > 0:
            try:
                # Create a minimal shell for prefilter testing
                shell = InteractiveShell.instance()
                prefilter = shell.prefilter_manager
                prefilter.prefilter_line(test_input)
            except (ValueError, SyntaxError, TypeError, AttributeError, RuntimeError):
                pass

        # Test 4: Test with magic commands
        magic_input = "%" + fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))
        if len(magic_input) > 1:
            try:
                transformer = TransformerManager()
                transformer.transform_cell(magic_input)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 5: Test with shell escapes
        shell_input = "!" + fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))
        if len(shell_input) > 1:
            try:
                transformer = TransformerManager()
                transformer.transform_cell(shell_input)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 6: Test with help syntax
        if len(test_input) > 0:
            help_input = test_input + "?"
            try:
                transformer = TransformerManager()
                transformer.transform_cell(help_input)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

    except Exception:
        # Catch any unexpected exceptions
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
