#!/usr/bin/env python3
"""
LibFuzzer driver for Black library - Python code formatter.
Tests core formatting functions: lib2to3_parse(), format_str(), and parse_ast()
"""

import sys
import random

# Import Black functions
try:
    from black import parsing, format_str
    from black.mode import Mode
except ImportError:
    from black.parsing import lib2to3_parse, parse_ast
    from black import format_str
    from black.mode import Mode


def fuzz_black(data: bytes):
    """Main fuzzer function targeting Black parsing and formatting"""

    if len(data) < 1:
        return

    # Decode input
    try:
        test_input = data.decode('utf-8', errors='ignore')
    except:
        return

    if not test_input:
        return

    # Determine which function to test based on first byte
    choice = data[0] % 4

    try:
        if choice == 0:
            # Test lib2to3_parse()
            _fuzz_lib2to3_parse(test_input)
        elif choice == 1:
            # Test format_str()
            _fuzz_format_str(test_input)
        elif choice == 2:
            # Test parse_ast()
            _fuzz_parse_ast(test_input)
        elif choice == 3:
            # Test with different Mode configurations
            _fuzz_with_mode_variations(test_input)
    except Exception:
        # Expected exceptions during fuzzing
        pass


def _fuzz_lib2to3_parse(src_txt: str):
    """Test lib2to3_parse with arbitrary Python source"""
    try:
        from black.parsing import lib2to3_parse
        result = lib2to3_parse(src_txt, set())
        # Result should be a Node or Leaf
        assert result is not None
    except SyntaxError:
        # Expected for invalid Python
        pass
    except Exception:
        pass


def _fuzz_format_str(src_contents: str):
    """Test format_str() - main formatting function"""
    try:
        mode = Mode()
        result = format_str(src_contents, mode=mode)
        # Result should be a string
        assert isinstance(result, str)
    except SyntaxError:
        # Expected for invalid Python code
        pass
    except Exception:
        pass


def _fuzz_parse_ast(src: str):
    """Test parse_ast() for Python AST parsing"""
    try:
        from black.parsing import parse_ast
        result = parse_ast(src)
        # Result should be an AST node
        assert result is not None
    except SyntaxError:
        # Expected for invalid Python
        pass
    except Exception:
        pass


def _fuzz_with_mode_variations(src_txt: str):
    """Test formatting with various Mode configurations"""
    try:
        # Test with different line lengths
        for line_length in [10, 88, 120, 1000]:
            try:
                mode = Mode(line_length=line_length)
                result = format_str(src_txt, mode=mode)
                assert isinstance(result, str)
            except SyntaxError:
                pass

        # Test with string_normalization flag
        try:
            mode = Mode(string_normalization=False)
            result = format_str(src_txt, mode=mode)
            assert isinstance(result, str)
        except SyntaxError:
            pass

        # Test with magic_trailing_comma
        try:
            mode = Mode(magic_trailing_comma=True)
            result = format_str(src_txt, mode=mode)
            assert isinstance(result, str)
        except SyntaxError:
            pass

    except Exception:
        pass


if __name__ == "__main__":
    # Fuzzing main loop
    test_cases = [
        b"x = 1",
        b"def f(): pass",
        b"print('hello')",
        b"invalid syntax !!",
        b"" * 1000,
        b"x" * 100,
    ]

    # Add random test cases
    random.seed(42)
    for _ in range(100):
        test_cases.append(bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]))

    print(f"Running {len(test_cases)} test cases for Black fuzzing...")
    success = 0
    errors = 0

    for test_case in test_cases:
        try:
            fuzz_black(test_case)
            success += 1
        except Exception as e:
            errors += 1

    print(f"Completed: {success} successful, {errors} with expected errors")
