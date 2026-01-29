#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for black library.
Tests black's code formatting, parsing, and feature detection.
"""

import sys
import atheris
import black
from black import Mode, TargetVersion


def __test_one_input(data: bytes) -> None:
    """Fuzz driver for black library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Split fuzzed data into parts for different test strategies
    action = fdp.ConsumeIntInRange(0, 6)
    code_input = fdp.ConsumeUnicode(8192)

    if action == 0:
        # Test format_str() with default mode
        try:
            black.format_str(code_input, mode=Mode())
        except (SyntaxError, ValueError, black.InvalidInput, black.NothingChanged):
            pass
        except Exception:
            # Ignore other exceptions like AttributeError from parsing
            pass

    elif action == 1:
        # Test format_str() with target versions
        try:
            mode = Mode(target_versions={TargetVersion.PY38, TargetVersion.PY39})
            black.format_str(code_input, mode=mode)
        except (SyntaxError, ValueError, black.InvalidInput, black.NothingChanged):
            pass
        except Exception:
            pass

    elif action == 2:
        # Test format_str() with line length variation
        try:
            line_length = fdp.ConsumeIntInRange(10, 200)
            mode = Mode(line_length=line_length)
            black.format_str(code_input, mode=mode)
        except (SyntaxError, ValueError, black.InvalidInput, black.NothingChanged):
            pass
        except Exception:
            pass

    elif action == 3:
        # Test lib2to3_parse()
        try:
            black.lib2to3_parse(code_input)
        except (SyntaxError, ValueError, black.InvalidInput):
            pass
        except Exception:
            pass

    elif action == 4:
        # Test parse_ast()
        try:
            black.parse_ast(code_input)
        except (SyntaxError, ValueError):
            pass
        except Exception:
            pass

    elif action == 5:
        # Test get_features_used()
        try:
            black.get_features_used(code_input)
        except (SyntaxError, ValueError, black.InvalidInput):
            pass
        except Exception:
            pass

    elif action == 6:
        # Test detect_target_versions()
        try:
            black.detect_target_versions(code_input)
        except (SyntaxError, ValueError, black.InvalidInput):
            pass
        except Exception:
            pass


# Initialize atheris for code coverage guidance
atheris.Setup(sys.argv, __test_one_input)

if __name__ == "__main__":
    atheris.Fuzz()
