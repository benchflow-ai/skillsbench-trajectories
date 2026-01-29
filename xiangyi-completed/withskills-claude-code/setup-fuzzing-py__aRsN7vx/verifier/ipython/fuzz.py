#!/usr/bin/env python3
"""
Fuzz driver for IPython interactive shell.
Targets the input transformation and code compilation functions.
"""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core import inputtransformer2
    from IPython.core import compilerop


def TestOneInput(data):
    """Fuzz entry point for IPython input processing."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 1)

    try:
        if choice == 0:
            # Fuzz input transformers
            code_lines = []
            num_lines = fdp.ConsumeIntInRange(1, 10)
            for _ in range(num_lines):
                line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
                code_lines.append(line)

            code = '\n'.join(code_lines)

            try:
                # Try various transformers
                transformed = inputtransformer2.TransformerManager().transform_cell(code)
            except (SyntaxError, ValueError, IndexError, KeyError, AttributeError):
                pass  # Expected exceptions

        elif choice == 1:
            # Fuzz code compilation
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            filename = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(5, 50))

            try:
                compiler = compilerop.CachingCompiler()
                # Try to compile the code
                result = compiler(code, filename, 'exec')
            except (SyntaxError, ValueError, OverflowError, MemoryError):
                pass  # Expected exceptions

    except Exception as e:
        # Catch any unexpected exceptions
        exception_type = type(e).__name__
        safe_exceptions = [
            'SyntaxError', 'ValueError', 'IndexError', 'KeyError', 'AttributeError',
            'TypeError', 'OverflowError', 'MemoryError', 'RecursionError',
            'UnicodeDecodeError', 'OSError'
        ]
        if exception_type not in safe_exceptions:
            raise  # Re-raise unexpected exceptions


def main():
    """Main entry point for fuzzing."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
