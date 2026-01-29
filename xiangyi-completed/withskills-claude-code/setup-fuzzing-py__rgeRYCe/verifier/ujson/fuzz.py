"""
LibFuzzer fuzz driver for ujson (UltraJSON) library.

Targets:
- ujson.loads() - JSON decoder
- ujson.dumps() - JSON encoder
- String and numeric parsing
"""

import sys
import ujson

def fuzz(data):
    """Main fuzzing target for ujson library."""
    if not data:
        return

    try:
        # Test 1: JSON decoding
        try:
            # Try to decode as UTF-8
            json_string = data.decode('utf-8', errors='ignore')

            if json_string and len(json_string) < 100000:
                # Attempt to parse as JSON
                result = ujson.loads(json_string)
                if result is not None:
                    # Test encoding the result back
                    try:
                        encoded = ujson.dumps(result)
                        if encoded:
                            pass
                    except (TypeError, ValueError, OverflowError):
                        pass
        except (ValueError, ujson.JSONDecodeError, UnicodeDecodeError,
                OverflowError, TypeError):
            pass
        except Exception:
            pass

        # Test 2: Raw bytes decoding
        try:
            if len(data) < 100000:
                result = ujson.loads(data)
                if result is not None:
                    pass
        except (ValueError, ujson.JSONDecodeError, UnicodeDecodeError,
                OverflowError, TypeError):
            pass
        except Exception:
            pass

        # Test 3: Encoding various Python objects
        try:
            test_objects = [
                data[:10],  # bytes
                data.decode('utf-8', errors='ignore')[:100],  # string
                len(data),  # integer
                float(len(data)),  # float
                bool(data),  # boolean
                None,  # null
            ]

            for obj in test_objects:
                try:
                    encoded = ujson.dumps(obj)
                    if encoded:
                        # Try to decode back
                        decoded = ujson.loads(encoded)
                except (TypeError, ValueError, OverflowError):
                    pass
        except Exception:
            pass

    except Exception:
        pass


if __name__ == '__main__':
    # Simple test mode
    test_json = b'{"key": "value", "number": 42}'
    fuzz(test_json)
    print("Fuzz target ready")
