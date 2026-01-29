#!/usr/bin/env python3
"""
Atheris-based fuzzer for IPython library
Targets: input transformation and code execution functions
"""

import sys
import atheris

# Suppress output for cleaner fuzzing
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input, LineInfo
    from IPython.core.prefilter import PrefilterManager
    from IPython.core.interactiveshell import InteractiveShell


def TestOneInput(data):
    """Fuzz entry point called by Atheris"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz TransformerManager.transform_cell()
            tm = TransformerManager()
            cell = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            tm.transform_cell(cell)

        elif choice == 1:
            # Fuzz split_user_input()
            line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            split_user_input(line)

        elif choice == 2:
            # Fuzz PrefilterManager
            pm = PrefilterManager()
            line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            pm.prefilter_line(line)

        elif choice == 3:
            # Fuzz TransformerManager.check_complete()
            tm = TransformerManager()
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 300))
            tm.check_complete(code)

        elif choice == 4:
            # Fuzz various IPython escape sequences
            tm = TransformerManager()
            escape_char = fdp.PickValueInList(['!', '!!', '?', '??', '%', '%%', ',', ';', '/'])
            rest = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 100))
            cell = escape_char + rest
            tm.transform_cell(cell)

    except (SyntaxError, ValueError, TypeError, AttributeError,
            IndentationError, KeyError, IndexError, UnicodeDecodeError):
        # Expected exceptions during fuzzing
        pass
    except Exception as e:
        # Catch unexpected exceptions
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["maximum recursion", "not found", "no module"]):
            pass
        else:
            # Re-raise to find bugs
            raise


def main():
    """Initialize and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
