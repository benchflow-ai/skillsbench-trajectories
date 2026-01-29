#!/usr/bin/env python3
"""
Fuzz driver for IPython library - interactive Python shell
Uses Atheris (LibFuzzer-based) for coverage-guided fuzzing
"""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.compilerop import CachingCompiler
    import IPython.utils.text

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for IPython library"""
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 2)

    if choice == 0:
        # Fuzz input transformation
        try:
            user_input = fdp.ConsumeUnicodeNoSurrogates(500)
            if user_input:
                transformer = TransformerManager()
                transformed = transformer.transform_cell(user_input)
        except (ValueError, TypeError, SyntaxError):
            pass

    elif choice == 1:
        # Fuzz text utilities
        try:
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            if text:
                # Test various text utilities
                IPython.utils.text.wrap_paragraphs(text, ncols=80)
                IPython.utils.text.strip_ansi(text)
        except (ValueError, TypeError):
            pass

    elif choice == 2:
        # Fuzz compiler
        try:
            code = fdp.ConsumeUnicodeNoSurrogates(300)
            if code:
                compiler = CachingCompiler()
                compiler(code, '<fuzz>', 'exec')
        except (SyntaxError, ValueError, TypeError, MemoryError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
