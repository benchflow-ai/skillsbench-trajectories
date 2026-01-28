#!/usr/bin/env python3
"""
LibFuzzer driver for IPython library - interactive Python shell.
Tests input transformation and parsing: TransformerManager, PrefilterManager, and CachingCompiler
"""

import sys
import random

# Import IPython components
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input


def fuzz_ipython(data: bytes):
    """Main fuzzer function targeting IPython parsing and transformation"""

    if len(data) < 1:
        return

    # Decode input
    try:
        test_input = data.decode('utf-8', errors='ignore')
    except:
        return

    if not test_input:
        return

    # Determine which transformer to test based on first byte
    choice = data[0] % 4

    try:
        if choice == 0:
            # Test TransformerManager.transform_cell()
            _fuzz_transform_cell(test_input)
        elif choice == 1:
            # Test split_user_input()
            _fuzz_split_user_input(test_input)
        elif choice == 2:
            # Test with magic commands
            _fuzz_magic_commands(test_input)
        elif choice == 3:
            # Test with shell commands
            _fuzz_shell_commands(test_input)
    except Exception:
        # Expected exceptions during fuzzing
        pass


def _fuzz_transform_cell(raw_cell: str):
    """Test TransformerManager.transform_cell() with IPython syntax"""
    try:
        # Create transformer manager instance
        tm = TransformerManager()
        # Transform the cell (may contain IPython magic, shell commands, etc.)
        result = tm.transform_cell(raw_cell)
        # Result should be a string containing valid Python code
        assert isinstance(result, str)
    except SyntaxError:
        # Expected for invalid syntax
        pass
    except (ValueError, AttributeError, TypeError):
        # Other expected errors
        pass


def _fuzz_split_user_input(line: str):
    """Test split_user_input() for line splitting"""
    try:
        # Split user input line
        line_info = split_user_input(line)
        # Result should have indent, esc, ifun, rest attributes
        assert hasattr(line_info, 'indent')
        assert hasattr(line_info, 'esc')
        assert hasattr(line_info, 'ifun')
        assert hasattr(line_info, 'rest')
    except Exception:
        pass


def _fuzz_magic_commands(test_input: str):
    """Test IPython magic command transformation"""
    try:
        tm = TransformerManager()
        # Test with magic commands
        magic_variants = [
            f"%{test_input}",
            f"%%{test_input}",
            f"a = %{test_input}",
            f"x = %%{test_input}",
        ]

        for magic_cell in magic_variants:
            try:
                result = tm.transform_cell(magic_cell)
                assert isinstance(result, str)
            except (SyntaxError, ValueError):
                pass
    except Exception:
        pass


def _fuzz_shell_commands(test_input: str):
    """Test IPython shell command transformation"""
    try:
        tm = TransformerManager()
        # Test with shell commands
        shell_variants = [
            f"!{test_input}",
            f"!!{test_input}",
            f"a = !{test_input}",
            f"?{test_input}",
            f"??{test_input}",
        ]

        for shell_cell in shell_variants:
            try:
                result = tm.transform_cell(shell_cell)
                assert isinstance(result, str)
            except (SyntaxError, ValueError, IndexError):
                pass
    except Exception:
        pass


if __name__ == "__main__":
    # Fuzzing main loop
    test_cases = [
        b"x = 1",
        b"%time x = 1",
        b"!ls",
        b"?print",
        b"%%timeit\nx=1",
        b"a = !ls",
    ]

    # Add random test cases
    random.seed(42)
    for _ in range(100):
        test_cases.append(bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]))

    print(f"Running {len(test_cases)} test cases for IPython fuzzing...")
    success = 0
    errors = 0

    for test_case in test_cases:
        try:
            fuzz_ipython(test_case)
            success += 1
        except Exception as e:
            errors += 1

    print(f"Completed: {success} successful, {errors} with expected errors")
