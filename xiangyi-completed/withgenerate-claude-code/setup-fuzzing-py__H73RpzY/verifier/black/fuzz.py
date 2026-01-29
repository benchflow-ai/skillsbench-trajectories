#!/usr/bin/env python3
"""Fuzz driver for Black - Python code formatter"""

import atheris
import sys

# Import black for fuzzing
import black


@atheris.instrument_func
def test_one(data):
    """Fuzz driver for black formatter"""
    if len(data) < 1:
        return

    # Test 1: format_str with default mode
    try:
        src_code = data.decode('utf-8', errors='ignore')
        if len(src_code) < 10000:  # Reasonable code size
            mode = black.Mode()
            result = black.format_str(src_code, mode=mode)
    except black.NothingChanged:
        # Expected - code already formatted
        pass
    except (SyntaxError, ValueError, TypeError):
        # Expected for invalid code
        pass
    except Exception:
        raise

    # Test 2: lib2to3_parse
    try:
        src_code = data.decode('utf-8', errors='ignore')
        if len(src_code) < 10000:
            # Test with default Python 3.8+ target
            result = black.lib2to3_parse(src_code, {black.TargetVersion.PY38})
    except black.parsing.InvalidInput:
        pass
    except (SyntaxError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 3: format_str with different line lengths
    try:
        src_code = data.decode('utf-8', errors='ignore')
        if len(src_code) < 10000 and len(src_code) > 0:
            for line_length in [88, 120, 79]:
                mode = black.Mode(line_length=line_length)
                result = black.format_str(src_code, mode=mode)
    except black.NothingChanged:
        pass
    except (SyntaxError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 4: format_str with string normalization disabled
    try:
        src_code = data.decode('utf-8', errors='ignore')
        if len(src_code) < 10000:
            mode = black.Mode(string_normalization=False)
            result = black.format_str(src_code, mode=mode)
    except black.NothingChanged:
        pass
    except (SyntaxError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 5: parse_ast
    try:
        src_code = data.decode('utf-8', errors='ignore')
        if len(src_code) < 10000:
            result = black.parse_ast(src_code)
    except (SyntaxError, ValueError, TypeError):
        pass
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
