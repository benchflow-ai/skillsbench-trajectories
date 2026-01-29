#!/usr/bin/env python3
"""LibFuzzer harness for IPython interactive shell."""

import sys
import atheris

try:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.inputtransformer2 import TransformerManager
except ImportError as e:
    print(f"Failed to import IPython: {e}", file=sys.stderr)
    sys.exit(1)


def fuzz_ipython_input_transform(data: bytes) -> None:
    """Fuzz IPython input transformation."""
    try:
        # Convert bytes to string
        input_str = data.decode('utf-8', errors='ignore')

        # Try to transform input
        try:
            transformer = TransformerManager()
            transformer.transform_cell(input_str)
        except (SyntaxError, ValueError, TypeError, AttributeError):
            pass

    except (UnicodeDecodeError, MemoryError, RuntimeError):
        pass


def fuzz_ipython_code_parsing(data: bytes) -> None:
    """Fuzz IPython code parsing."""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Try to check if input is complete
        try:
            from IPython.core.inputsplitter import InputSplitter
            splitter = InputSplitter()
            splitter.push(input_str)
        except Exception:
            pass

        # Try AST compilation
        try:
            compile(input_str, '<string>', 'exec')
        except SyntaxError:
            pass

    except Exception:
        pass


def fuzz_ipython_magic_parsing(data: bytes) -> None:
    """Fuzz IPython magic command parsing."""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Check if it looks like a magic command
        if input_str.startswith('%') or input_str.startswith('!'):
            # Try to parse as magic
            try:
                from IPython.core.prefilter import PrefilterManager
                from IPython.core.inputtransformer2 import TransformerManager
                transformer = TransformerManager()
                transformer.transform_cell(input_str)
            except Exception:
                pass

    except Exception:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing function."""
    fuzz_ipython_input_transform(data)
    fuzz_ipython_code_parsing(data)
    fuzz_ipython_magic_parsing(data)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
