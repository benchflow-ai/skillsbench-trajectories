#!/usr/bin/env python3
"""
Fuzz driver for IPython interactive shell.

Target: InteractiveShell.run_cell() - executes Python code
This tests IPython's code execution and magic command parsing.
"""

import sys
import atheris

# Import IPython with instrumentation
with atheris.instrument_imports():
    from IPython.terminal.interactiveshell import TerminalInteractiveShell
    from IPython.core.error import UsageError


# Global shell instance (reused across fuzzer runs)
shell = None


def TestOneInput(data):
    """
    Fuzz target for IPython code execution.

    Tests:
    - Python code execution
    - Magic command parsing (%cmd, %%cmd)
    - Syntax error handling

    Expected behavior:
    - Valid Python/magic commands execute without crashes
    - Invalid syntax raises SyntaxError
    - No shell crashes or hangs
    """
    global shell

    if len(data) == 0:
        return

    # Decode to string
    try:
        code = data.decode('utf-8', errors='ignore')
    except Exception:
        return

    # Skip empty or very long inputs
    if not code or len(code) > 5000:
        return

    # Initialize shell on first run
    if shell is None:
        try:
            # Create a minimal IPython shell instance
            # Use simple configuration to avoid GUI/external dependencies
            shell = TerminalInteractiveShell.instance()
        except Exception as e:
            # If shell initialization fails, skip fuzzing
            print(f"Warning: Could not initialize IPython shell: {e}")
            return

    # Fuzz run_cell()
    try:
        # run_cell executes the code and handles magic commands
        result = shell.run_cell(code, store_history=False)

        # result.success indicates if execution succeeded
        # Errors during execution are caught and don't raise exceptions

    except SyntaxError:
        # Expected for invalid Python syntax
        pass
    except UsageError:
        # Expected for invalid magic commands
        pass
    except (SystemExit, KeyboardInterrupt):
        # Code might try to exit - catch and continue
        pass
    except RecursionError:
        # Deep recursion
        pass
    except Exception as e:
        # Other exceptions might be concerning but IPython is robust
        # Let atheris decide if it's a real issue
        raise


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
