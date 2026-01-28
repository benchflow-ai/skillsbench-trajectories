#!/usr/bin/env python3
"""
Fuzz driver for IPython library - Interactive Python shell
Fuzzes input transformation which handles magic commands and special syntax.
"""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for IPython input transformer."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Create transformer manager
    manager = TransformerManager()

    # Test transform_cell() with fuzzer-generated code
    try:
        code_input = fdp.ConsumeUnicodeNoSurrogates(len(data))
        if code_input:
            manager.transform_cell(code_input)
    except (SyntaxError, ValueError, IndentationError):
        # Expected exceptions for invalid Python syntax
        pass
    except RecursionError:
        # Can happen with deeply nested structures
        pass
    except Exception as e:
        # Unexpected exception - potential bug
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
