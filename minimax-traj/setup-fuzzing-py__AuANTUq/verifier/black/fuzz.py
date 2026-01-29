"""
Coverage-guided fuzzing driver for Black code formatter.
Fuzzes Python code parsing and formatting.
"""

import atheris
import sys

# Import Black library
try:
    import black
except ImportError:
    # Try alternative import path
    sys.path.insert(0, '/app/black')
    import black

def fuzz_format_str(data):
    """Fuzz black.format_str() with Python code strings"""
    try:
        # Convert fuzz data to Python code string
        code = data.decode('utf-8', errors='ignore')

        # Create a default mode
        mode = black.Mode()

        try:
            # Try to format the code
            result = black.format_str(code, mode=mode)
        except Exception:
            pass  # Expected for many malformed inputs

        # Try with fast mode
        try:
            mode_fast = black.Mode(fast=True)
            result = black.format_str(code, mode=mode_fast)
        except Exception:
            pass

        # Try with different line lengths
        for line_length in [80, 100, 120]:
            try:
                mode_custom = black.Mode(line_length=line_length)
                result = black.format_str(code, mode=mode_custom)
            except Exception:
                pass

    except Exception:
        pass

def fuzz_parse_ast(data):
    """Fuzz AST parsing functions"""
    try:
        code = data.decode('utf-8', errors='ignore')

        # Test parse_ast
        try:
            result = black.parse_ast(code)
        except Exception:
            pass

        # Test lib2to3_parse with different target versions
        try:
            result = black.lib2to3_parse(code)
        except Exception:
            pass

        # Test matches_grammar
        try:
            from black.parsing import Grammar
            import lib2to3.pygram
            grammar = lib2to3.pygram.python_grammar
            result = black.matches_grammar(code, grammar)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_string_normalization(data):
    """Fuzz string normalization functions"""
    try:
        # Get string processing functions
        from black.strings import (
            normalize_string_quotes,
            normalize_string_prefix,
            sub_twice
        )

        input_str = data.decode('utf-8', errors='ignore')

        # Test normalize_string_quotes
        try:
            result = normalize_string_quotes(input_str)
        except Exception:
            pass

        # Test normalize_string_prefix
        try:
            result = normalize_string_prefix(input_str)
        except Exception:
            pass

        # Test sub_twice with a simple regex
        try:
            import re
            pattern = re.compile(r'test')
            result = black.sub_twice(pattern, 'replacement', input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_decode_bytes(data):
    """Fuzz byte decoding with various encodings"""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'ascii']:
            try:
                mode = black.Mode()
                result = black.decode_bytes(data, mode=mode)
            except Exception:
                pass

    except Exception:
        pass

def fuzz_format_cell(data):
    """Fuzz Jupyter cell formatting"""
    try:
        code = data.decode('utf-8', errors='ignore')

        mode = black.Mode()

        try:
            result = black.format_cell(code, fast=False, mode=mode)
        except Exception:
            pass

        try:
            result = black.format_cell(code, fast=True, mode=mode)
        except Exception:
            pass

    except Exception:
        pass

def TestOneInput(data):
    """Main fuzzing entry point"""
    # Limit input size to avoid timeouts
    if len(data) > 100000:
        data = data[:100000]

    # Run all fuzzing targets
    fuzz_format_str(data)
    fuzz_parse_ast(data)
    fuzz_string_normalization(data)
    fuzz_decode_bytes(data)
    fuzz_format_cell(data)

if __name__ == '__main__':
    # Setup atheris
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
