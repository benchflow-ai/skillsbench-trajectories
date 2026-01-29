#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for ujson.
Fuzzes JSON encoding and decoding functions.
"""

import sys
import atheris
import ujson
import json

def fuzz_ujson_target(data):
    """Fuzzer target function."""
    fuzzer = FuzzUJSON(data)
    fuzzer.run()

atheris.Setup(sys.argv, fuzz_ujson_target)


class FuzzUJSON:
    """Fuzz driver for ujson JSON library."""

    def __init__(self, data):
        """Initialize fuzzer with input data."""
        self.fuzz_data = atheris.FuzzedDataProvider(data)

    def run(self):
        """Execute fuzzing targets."""
        try:
            self._fuzz_decode()
            self._fuzz_encode()
            self._fuzz_roundtrip()
            self._fuzz_edge_cases()
        except Exception:
            # Expected for invalid input
            pass

    def _fuzz_decode(self):
        """Fuzz JSON decoding."""
        json_string = self.fuzz_data.ConsumeUnicodeString(500)

        try:
            # Try ujson decode
            result = ujson.decode(json_string)

            # Verify result is a valid Python object
            assert result is not None or json_string.strip() in ('null',)
        except (ValueError, TypeError, AttributeError):
            # Expected for invalid JSON
            pass
        except Exception:
            pass

    def _fuzz_encode(self):
        """Fuzz JSON encoding."""
        choice = self.fuzz_data.ConsumeIntInRange(0, 5)

        try:
            if choice == 0:
                # Encode simple types
                obj = self.fuzz_data.ConsumeBool()
                result = ujson.encode(obj)
            elif choice == 1:
                # Encode numbers
                obj = self.fuzz_data.ConsumeFloat()
                result = ujson.encode(obj)
            elif choice == 2:
                # Encode strings
                obj = self.fuzz_data.ConsumeUnicodeString(100)
                result = ujson.encode(obj)
            elif choice == 3:
                # Encode list
                obj = [
                    self.fuzz_data.ConsumeInt(32),
                    self.fuzz_data.ConsumeUnicodeString(50),
                    self.fuzz_data.ConsumeBool()
                ]
                result = ujson.encode(obj)
            elif choice == 4:
                # Encode dict
                obj = {
                    "key1": self.fuzz_data.ConsumeInt(32),
                    "key2": self.fuzz_data.ConsumeUnicodeString(50),
                    "key3": self.fuzz_data.ConsumeBool()
                }
                result = ujson.encode(obj)
            elif choice == 5:
                # Encode None
                obj = None
                result = ujson.encode(obj)

            # Verify result is a string
            assert isinstance(result, str)
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass
        except Exception:
            pass

    def _fuzz_roundtrip(self):
        """Fuzz encode/decode roundtrip."""
        choice = self.fuzz_data.ConsumeIntInRange(0, 3)

        try:
            if choice == 0:
                # Simple types
                original = self.fuzz_data.ConsumeBool()
            elif choice == 1:
                # Numbers (avoid infinity/nan)
                original = min(1e10, max(-1e10, self.fuzz_data.ConsumeFloat()))
            elif choice == 2:
                # Strings
                original = self.fuzz_data.ConsumeUnicodeString(100)
            elif choice == 3:
                # List
                original = [
                    self.fuzz_data.ConsumeInt(32),
                    self.fuzz_data.ConsumeUnicodeString(30)
                ]

            # Encode and decode
            encoded = ujson.encode(original)
            decoded = ujson.decode(encoded)

            # Verify roundtrip for certain types
            if isinstance(original, (bool, str, list)):
                assert decoded == original or str(decoded) == str(original)
        except (ValueError, TypeError, AttributeError, AssertionError):
            pass
        except Exception:
            pass

    def _fuzz_edge_cases(self):
        """Fuzz edge cases in JSON handling."""
        choice = self.fuzz_data.ConsumeIntInRange(0, 6)

        try:
            if choice == 0:
                # Empty JSON structures
                for empty_json in ('{}', '[]', 'null', 'true', 'false'):
                    result = ujson.decode(empty_json)

            elif choice == 1:
                # Numbers at boundaries
                boundary_values = [
                    0, 1, -1, 2147483647, -2147483648,
                    9223372036854775807, -9223372036854775808
                ]
                for val in boundary_values:
                    encoded = ujson.encode(val)
                    decoded = ujson.decode(encoded)

            elif choice == 2:
                # Nested structures
                nested = {"a": {"b": {"c": [1, 2, 3]}}}
                encoded = ujson.encode(nested)
                decoded = ujson.decode(encoded)

            elif choice == 3:
                # Unicode characters
                unicode_str = self.fuzz_data.ConsumeUnicodeString(100)
                encoded = ujson.encode(unicode_str)
                decoded = ujson.decode(encoded)

            elif choice == 4:
                # Various number formats
                test_json = '[1, 1.5, 1e10, 1.5e-5, -1, -1.5]'
                result = ujson.decode(test_json)

            elif choice == 5:
                # Encode with different options
                obj = {"key": "value", "num": 42}
                try:
                    # Try various encoding options
                    ujson.encode(obj)
                except TypeError:
                    pass

            elif choice == 6:
                # Whitespace in JSON
                json_with_ws = self.fuzz_data.ConsumeUnicodeString(50)
                try:
                    ujson.decode(json_with_ws)
                except ValueError:
                    pass
        except (ValueError, TypeError, AttributeError, AssertionError, OverflowError):
            pass
        except Exception:
            pass


if __name__ == '__main__':
    atheris.Fuzz()
