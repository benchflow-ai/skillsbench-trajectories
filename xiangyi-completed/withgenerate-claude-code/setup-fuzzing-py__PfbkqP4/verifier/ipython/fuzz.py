#!/usr/bin/env python3
"""Coverage-guided fuzzing for IPython library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for IPython library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import IPython components inside to ensure instrumentation
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.compilerop import CachingCompiler
    from IPython.core.splitinput import split_user_input

    # Test 1: Transform cell with IPython syntax
    try:
        cell = fdp.ConsumeUnicodeNoSurrogates(2000)
        if cell:
            tm = TransformerManager()
            tm.transform_cell(cell)
    except (SyntaxError, ValueError, TypeError, RuntimeError,
            OverflowError, MemoryError, RecursionError):
        pass
    except Exception as e:
        # Catch tokenize errors
        if "tokenize" in type(e).__module__:
            pass
        else:
            raise

    # Test 2: Check code completeness
    try:
        cell = fdp.ConsumeUnicodeNoSurrogates(1000)
        if cell:
            tm = TransformerManager()
            result = tm.check_complete(cell)
            # result is ('complete'|'incomplete'|'invalid', indent|None)
    except (SyntaxError, ValueError, TypeError, RuntimeError,
            OverflowError, MemoryError, RecursionError):
        pass
    except Exception as e:
        if "tokenize" in type(e).__module__:
            pass
        else:
            raise

    # Test 3: Parse to AST
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(1000)
        if code:
            compiler = CachingCompiler()
            compiler.ast_parse(code)
    except (SyntaxError, ValueError, TypeError, RuntimeError,
            OverflowError, MemoryError, RecursionError):
        pass

    # Test 4: Split user input
    try:
        line = fdp.ConsumeUnicodeNoSurrogates(500)
        if line:
            split_user_input(line)
    except (SyntaxError, ValueError, TypeError, RuntimeError):
        pass

    # Test 5: Transform with special IPython syntax patterns
    try:
        # Generate input with IPython escape characters
        escape_chars = ["!", "!!", "?", "??", "%", "%%", ",", ";", "/"]
        escape = escape_chars[fdp.ConsumeIntInRange(0, len(escape_chars) - 1)]
        content = fdp.ConsumeUnicodeNoSurrogates(200)
        cell = escape + content
        tm = TransformerManager()
        tm.transform_cell(cell)
    except (SyntaxError, ValueError, TypeError, RuntimeError,
            OverflowError, MemoryError, RecursionError):
        pass
    except Exception as e:
        if "tokenize" in type(e).__module__:
            pass
        else:
            raise


def main():
    # Instrument imports
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
