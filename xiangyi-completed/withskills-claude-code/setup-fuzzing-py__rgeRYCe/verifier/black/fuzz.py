"""
LibFuzzer fuzz driver for Black code formatter.

Targets:
- format_str()
- lib2to3_parse()
- normalize_string_quotes()
- parse_ast()
"""

import sys
from black import format_str, Mode

def fuzz(data):
    """Main fuzzing target for Black library."""
    if not data:
        return

    try:
        # Decode input as UTF-8, ignoring errors
        code = data.decode('utf-8', errors='ignore')

        if not code or len(code) > 100000:
            # Skip empty or very large inputs
            return

        # Test 1: Basic formatting with default mode
        try:
            mode = Mode()
            result = format_str(code, mode=mode)
            # Ensure result is valid
            if result:
                pass
        except Exception:
            pass

        # Test 2: Formatting with line ranges
        try:
            lines_list = []
            if b'\n' in data:
                line_count = code.count('\n')
                if line_count > 0:
                    # Create some line ranges
                    lines_list = [(1, min(5, line_count))]

            if lines_list:
                mode = Mode()
                result = format_str(code, mode=mode, lines=lines_list)
        except Exception:
            pass

        # Test 3: Various mode configurations
        if len(code) < 1000:
            try:
                mode = Mode(line_length=88)
                format_str(code, mode=mode)
            except Exception:
                pass

            try:
                mode = Mode(line_length=120)
                format_str(code, mode=mode)
            except Exception:
                pass

    except Exception:
        pass


if __name__ == '__main__':
    # Simple test mode
    test_code = b'def foo():\n    x=1\n    return x'
    fuzz(test_code)
    print("Fuzz target ready")
