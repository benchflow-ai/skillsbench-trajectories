"""Coverage-guided fuzz driver for IPython input transformation and compilation."""
import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import (
        TransformerManager,
        leading_empty_lines,
        leading_indent,
    )
    from IPython.core.compilerop import CachingCompiler
    from IPython.core.splitinput import LineInfo


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz TransformerManager.transform_cell()
        cell = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            tm = TransformerManager()
            tm.transform_cell(cell)
        except (SyntaxError, ValueError, TypeError, OverflowError,
                IndentationError, UnicodeDecodeError, RecursionError,
                AttributeError, IndexError, KeyError, TokenError):
            pass

    elif choice == 1:
        # Fuzz CachingCompiler with arbitrary source
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            compiler = CachingCompiler()
            compiler(src, "<fuzz>", "exec")
        except (SyntaxError, ValueError, TypeError, OverflowError,
                IndentationError, UnicodeDecodeError, RecursionError):
            pass

    elif choice == 2:
        # Fuzz leading_empty_lines and leading_indent helpers
        num_lines = fdp.ConsumeIntInRange(0, 20)
        lines = []
        for _ in range(num_lines):
            line = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 80))
            lines.append(line + "\n")
        try:
            leading_empty_lines(lines)
            leading_indent(lines)
        except (ValueError, TypeError, IndexError):
            pass

    elif choice == 3:
        # Fuzz TransformerManager.check_complete()
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            tm = TransformerManager()
            tm.check_complete(src)
        except (SyntaxError, ValueError, TypeError, OverflowError,
                IndentationError, UnicodeDecodeError, RecursionError,
                AttributeError, IndexError, TokenError):
            pass


from tokenize import TokenError

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
