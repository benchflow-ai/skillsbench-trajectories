#!/usr/bin/env python3
"""Fuzz driver for IPython - interactive shell"""

import atheris
import sys

# Import IPython components for fuzzing
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input


@atheris.instrument_func
def test_one(data):
    """Fuzz driver for IPython input transformation"""
    if len(data) < 1:
        return

    # Test 1: TransformerManager.transform_cell
    try:
        cell_code = data.decode('utf-8', errors='ignore')
        if len(cell_code) < 10000:
            transformer = TransformerManager()
            result = transformer.transform_cell(cell_code)
    except (SyntaxError, ValueError, IndentationError, AttributeError):
        pass
    except Exception:
        raise

    # Test 2: split_user_input
    try:
        line = data[:min(len(data), 1000)].decode('utf-8', errors='ignore')
        result = split_user_input(line)
    except (SyntaxError, ValueError, AttributeError):
        pass
    except Exception:
        raise

    # Test 3: Transform with various escape sequences
    try:
        cell_code = data.decode('utf-8', errors='ignore')
        if len(cell_code) < 10000 and len(cell_code) > 0:
            transformer = TransformerManager()

            # Test with escape sequences
            test_inputs = [
                "%" + cell_code[:100],  # Line magic
                "%%" + cell_code[:100],  # Cell magic
                "!" + cell_code[:100],  # System command
                "!!" + cell_code[:100],  # System capture
                cell_code + "?",  # Help
                cell_code + "??",  # Extended help
            ]

            for test_input in test_inputs:
                try:
                    result = transformer.transform_cell(test_input)
                except:
                    pass
    except Exception:
        raise

    # Test 4: Multi-line cell input
    try:
        cell_code = data.decode('utf-8', errors='ignore')
        if len(cell_code) < 10000:
            # Create multi-line input
            lines = cell_code.split('\n')
            multi_line = '\n'.join(lines[:min(len(lines), 50)])

            transformer = TransformerManager()
            result = transformer.transform_cell(multi_line)
    except (SyntaxError, ValueError, IndentationError):
        pass
    except Exception:
        raise

    # Test 5: Escape character detection
    try:
        line = data.decode('utf-8', errors='ignore')
        if len(line) < 1000:
            # Test split_user_input with various escape chars
            for escape_char in ['%', '!', '?', ',', ';', '/']:
                test_line = escape_char + line
                result = split_user_input(test_line)
    except (SyntaxError, ValueError):
        pass
    except Exception:
        raise

    # Test 6: Comment and special character handling
    try:
        cell_code = data.decode('utf-8', errors='ignore')
        if len(cell_code) < 10000:
            # Test with comments
            test_cell = "# Comment\n" + cell_code

            transformer = TransformerManager()
            result = transformer.transform_cell(test_cell)
    except (SyntaxError, ValueError, IndentationError):
        pass
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
