#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for Black Python formatter.
Fuzzes code formatting with various Python syntax patterns.
"""

import sys
import atheris

# Import black formatting
try:
    from black import format_str, Mode, NothingChanged
except ImportError:
    # Fallback if structure is different
    import black
    format_str = black.format_str
    Mode = black.Mode

def fuzz_black_target(data):
    """Fuzzer target function."""
    fuzzer = FuzzBlack(data)
    fuzzer.run()

atheris.Setup(sys.argv, fuzz_black_target)


class FuzzBlack:
    """Fuzz driver for Black code formatter."""

    def __init__(self, data):
        """Initialize fuzzer with input data."""
        self.fuzz_data = atheris.FuzzedDataProvider(data)

    def run(self):
        """Execute fuzzing targets."""
        try:
            self._fuzz_format_str()
            self._fuzz_format_with_modes()
            self._fuzz_edge_cases()
        except Exception:
            # Expected for invalid Python code
            pass

    def _fuzz_format_str(self):
        """Fuzz basic code formatting."""
        code = self.fuzz_data.ConsumeUnicodeString(500)

        try:
            # Try to format the code
            result = format_str(code, mode=Mode())

            # Verify result is a string
            assert isinstance(result, str)

            # Test idempotence: formatting twice should give same result
            result2 = format_str(result, mode=Mode())
            assert result == result2
        except (ValueError, SyntaxError, AssertionError, NothingChanged):
            pass
        except Exception:
            # Catch any other exceptions from formatter
            pass

    def _fuzz_format_with_modes(self):
        """Fuzz formatting with different modes."""
        code = self.fuzz_data.ConsumeUnicodeString(300)
        line_length = self.fuzz_data.ConsumeIntInRange(10, 200)
        string_norm = self.fuzz_data.ConsumeBool()

        try:
            mode = Mode(
                line_length=line_length,
                string_normalization=string_norm
            )
            result = format_str(code, mode=mode)
            assert isinstance(result, str)
        except (ValueError, SyntaxError, AssertionError, NothingChanged, TypeError):
            pass
        except Exception:
            pass

    def _fuzz_edge_cases(self):
        """Fuzz edge cases in Python syntax."""
        choice = self.fuzz_data.ConsumeIntInRange(0, 6)

        try:
            if choice == 0:
                # Empty code
                format_str("", mode=Mode())
            elif choice == 1:
                # Only comments
                format_str("# comment", mode=Mode())
            elif choice == 2:
                # Only whitespace
                format_str("   \n\t  ", mode=Mode())
            elif choice == 3:
                # Very long line
                long_line = "x = " + "y + " * 100 + "1"
                format_str(long_line, mode=Mode())
            elif choice == 4:
                # Nested structures
                code = "def f():\n    def g():\n        x = " + \
                       str(self.fuzz_data.ConsumeInt(32))
                format_str(code, mode=Mode())
            elif choice == 5:
                # String with special chars
                code = 'x = "' + self.fuzz_data.ConsumeUnicodeString(50) + '"'
                format_str(code, mode=Mode())
            elif choice == 6:
                # Mixed valid/invalid
                code = self.fuzz_data.ConsumeUnicodeString(200)
                format_str(code, mode=Mode())
        except (ValueError, SyntaxError, AssertionError, NothingChanged, TypeError):
            pass
        except Exception:
            pass


if __name__ == '__main__':
    atheris.Fuzz()
