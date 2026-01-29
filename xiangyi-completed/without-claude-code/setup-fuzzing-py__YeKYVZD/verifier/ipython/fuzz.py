#!/usr/bin/env python3
"""
Fuzzing driver for IPython library using Atheris (LibFuzzer for Python)
Targets: Input transformation, code completion, and magic command parsing
"""

import sys
import atheris

# Suppress warnings for cleaner fuzzing output
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    from IPython.core.completer import Completer
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython import get_ipython


def TestOneInput(data):
    """Fuzz target for IPython library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz code completer
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            completer = Completer(namespace={})
            completer.complete(text)

        elif choice == 1:
            # Fuzz input transformer
            lines = []
            num_lines = fdp.ConsumeIntInRange(1, 10)
            for _ in range(num_lines):
                line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
                lines.append(line)

            transformer = TransformerManager()
            for line in lines:
                try:
                    transformer.transform_cell(line)
                except:
                    pass

        elif choice == 2:
            # Fuzz with magic-like commands
            magic_prefix = fdp.PickValueInList(['%', '%%', '!', '?', '??'])
            command = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 300))
            full_command = magic_prefix + command

            transformer = TransformerManager()
            transformer.transform_cell(full_command)

    except (ValueError, TypeError, AttributeError, KeyError):
        # Expected exceptions
        pass
    except (SyntaxError, IndentationError):
        # Expected syntax errors
        pass
    except (UnicodeError, UnicodeDecodeError):
        # Expected encoding errors
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        error_type = type(e).__name__
        # Allow some known safe exceptions
        if error_type not in ['RecursionError', 'MemoryError', 'RuntimeError', 'OSError', 'IndexError']:
            raise


def main():
    """Main fuzzing entry point."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
