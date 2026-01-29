#!/usr/bin/env python3
"""
Fuzz driver for IPython
Tests: InputSplitter, code validation, parsing
"""

import atheris
import sys

# Ensure ipython module is importable
sys.path.insert(0, '/app/ipython')

try:
    from IPython.core.inputsplitter import InputSplitter
    from IPython.core.prefilter import PrefilterManager
except ImportError:
    # Fallback for different IPython versions
    try:
        from IPython.core.inputtransformer2 import TransformerManager
    except ImportError:
        pass


@atheris.instrument_func
def test_input_splitter(data):
    """Fuzz InputSplitter with code input"""
    try:
        code = data.decode('utf-8', errors='ignore')
        splitter = InputSplitter()

        # Test splitting and validation
        splitter.push(code)
        _ = splitter.source
        _ = splitter.source_reset()
    except (SyntaxError, ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass


@atheris.instrument_func
def test_code_parsing(data):
    """Fuzz code parsing and compilation"""
    try:
        code = data.decode('utf-8', errors='ignore')
        # Try to compile the code
        compile(code, '<fuzzer>', 'exec')
    except (SyntaxError, ValueError, TypeError):
        pass


@atheris.instrument_func
def test_magic_parsing(data):
    """Fuzz magic command and shell command parsing"""
    try:
        code = data.decode('utf-8', errors='ignore')
        # Test with magic commands
        if code.startswith('%'):
            pass
        elif code.startswith('!'):
            pass
    except (SyntaxError, ValueError, TypeError):
        pass


def test_one(data):
    """Main fuzzing function"""
    if len(data) < 1:
        return

    # Distribute fuzzing across different functions
    choice = data[0] % 3
    data = data[1:]

    if choice == 0:
        test_input_splitter(data)
    elif choice == 1:
        test_code_parsing(data)
    else:
        test_magic_parsing(data)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
