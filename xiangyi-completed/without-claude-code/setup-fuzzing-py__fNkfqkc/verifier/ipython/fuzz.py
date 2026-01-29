#!/usr/bin/env python3
"""
LibFuzzer-style fuzz driver for IPython library using Atheris.
Tests code execution, completion, and display functions.
"""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.terminal.interactiveshell import TerminalInteractiveShell
    from IPython.core.completer import IPCompleter
    from IPython.lib.pretty import pretty
    from IPython.core.display_functions import display


# Initialize IPython shell once
ip_shell = None


def TestOneInput(data):
    """Fuzz target for IPython library."""
    global ip_shell

    fdp = atheris.FuzzedDataProvider(data)

    # Skip empty inputs
    if len(data) < 1:
        return

    # Initialize shell lazily
    if ip_shell is None:
        ip_shell = TerminalInteractiveShell.instance()

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz run_cell with code input
            code = fdp.ConsumeUnicodeNoSurrogates(200)
            if code:
                try:
                    # Use silent mode to avoid output spam
                    ip_shell.run_cell(code, silent=True, store_history=False)
                except (SyntaxError, ValueError, TypeError, NameError, AttributeError):
                    pass

        elif choice == 1:
            # Fuzz IPCompleter.complete
            text = fdp.ConsumeUnicodeNoSurrogates(50)
            line_buffer = fdp.ConsumeUnicodeNoSurrogates(100)
            cursor_pos = fdp.ConsumeIntInRange(0, len(line_buffer)) if line_buffer else 0

            if text is not None:
                try:
                    ip_shell.complete(text, line_buffer, cursor_pos)
                except (ValueError, TypeError, AttributeError, IndexError):
                    pass

        elif choice == 2:
            # Fuzz pretty printing with various objects
            try:
                # Create various Python objects from fuzzed data
                obj_type = fdp.ConsumeIntInRange(0, 4)

                if obj_type == 0:
                    # String
                    obj = fdp.ConsumeUnicodeNoSurrogates(100)
                elif obj_type == 1:
                    # List
                    obj = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
                elif obj_type == 2:
                    # Dict
                    obj = {fdp.ConsumeString(10): fdp.ConsumeInt(4)
                          for _ in range(fdp.ConsumeIntInRange(0, 10))}
                elif obj_type == 3:
                    # Nested structure
                    obj = [[fdp.ConsumeInt(4)] for _ in range(fdp.ConsumeIntInRange(0, 5))]
                else:
                    # Number
                    obj = fdp.ConsumeInt(8)

                max_width = fdp.ConsumeIntInRange(10, 200)
                max_seq_length = fdp.ConsumeIntInRange(10, 1000)
                pretty(obj, max_width=max_width, max_seq_length=max_seq_length)
            except (ValueError, TypeError, AttributeError, RecursionError):
                pass

        elif choice == 3:
            # Fuzz run_cell_magic
            magic_name = fdp.ConsumeUnicodeNoSurrogates(20)
            line = fdp.ConsumeUnicodeNoSurrogates(50)
            cell = fdp.ConsumeUnicodeNoSurrogates(200)

            if magic_name:
                try:
                    ip_shell.run_cell_magic(magic_name, line, cell)
                except (ValueError, TypeError, AttributeError, KeyError):
                    pass

    except Exception as e:
        # Allow expected exceptions but catch unexpected crashes
        if not isinstance(e, (ValueError, TypeError, SyntaxError, NameError,
                            AttributeError, KeyError, IndexError, RecursionError,
                            RuntimeError)):
            raise


def main():
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
