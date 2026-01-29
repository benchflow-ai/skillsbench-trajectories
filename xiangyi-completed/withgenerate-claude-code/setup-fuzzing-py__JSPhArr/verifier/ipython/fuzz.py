#!/usr/bin/env python3
"""
Fuzzer for IPython - Interactive Python shell
Targets: Input transformation and code compilation
"""

import sys
import atheris

# Import after atheris setup
with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.compilerop import CachingCompiler


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz IPython input transformation and compilation."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Transform IPython cell syntax
    try:
        tm = TransformerManager()
        cell = fdp.ConsumeUnicodeNoSurrogates(300)
        if cell:
            transformed = tm.transform_cell(cell)
    except (SyntaxError, IndentationError, ValueError, TypeError,
            AttributeError, TokenError) as e:
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Catch other exceptions
        pass

    # Test 2: Test compilation
    try:
        compiler = CachingCompiler()
        code = fdp.ConsumeUnicodeNoSurrogates(200)
        if code:
            compiler(code, '<fuzz>', 'exec')
    except (SyntaxError, IndentationError, ValueError, TypeError,
            MemoryError, OverflowError) as e:
        # Expected exceptions
        pass
    except Exception as e:
        pass

    # Test 3: Test with IPython magic-like syntax
    try:
        tm = TransformerManager()
        # Generate IPython-like code with magics
        magic_chars = ['%', '!', '?']
        magic = fdp.PickValueInList(magic_chars)
        command = fdp.ConsumeUnicodeNoSurrogates(50)
        cell = f"{magic}{command}"

        if cell:
            transformed = tm.transform_cell(cell)
    except (SyntaxError, IndentationError, ValueError, TypeError,
            AttributeError) as e:
        pass
    except Exception as e:
        pass

    # Test 4: Test multi-line cells
    try:
        tm = TransformerManager()
        lines = []
        for _ in range(fdp.ConsumeIntInRange(1, 5)):
            line = fdp.ConsumeUnicodeNoSurrogates(50)
            lines.append(line)
        cell = "\n".join(lines)

        if cell:
            transformed = tm.transform_cell(cell)
    except (SyntaxError, IndentationError, ValueError, TypeError,
            AttributeError) as e:
        pass
    except Exception as e:
        pass


# Define TokenError if not available
try:
    from tokenize import TokenError
except ImportError:
    class TokenError(Exception):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
