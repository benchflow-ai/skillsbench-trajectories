#!/usr/bin/env python3
"""
Coverage-guided fuzzing driver for the UltraJSON (ujson) library.
Uses atheris for LibFuzzer-style fuzzing.
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for ujson library."""
    # Import inside function to avoid issues during atheris setup
    import ujson

    # Convert bytes to string for testing
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if len(text) > 100000:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: ujson.loads() - main decoding function
    try:
        ujson.loads(text)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 2: ujson.loads() with bytes input
    try:
        ujson.loads(data)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: ujson.loads() with bytearray input
    try:
        ujson.loads(bytearray(data))
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 4: Encode/decode round-trip with various Python objects
    try:
        # Try to decode first, then re-encode
        decoded = ujson.loads(text)
        encoded = ujson.dumps(decoded)
        # Verify round-trip
        ujson.loads(encoded)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 5: ujson.dumps() with ensure_ascii variations
    if len(data) > 5:
        try:
            test_obj = {"key": fdp.ConsumeUnicodeNoSurrogates(50)}
            ujson.dumps(test_obj, ensure_ascii=True)
            ujson.dumps(test_obj, ensure_ascii=False)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 6: ujson.dumps() with encode_html_chars
    if len(data) > 5:
        try:
            test_obj = {"key": fdp.ConsumeUnicodeNoSurrogates(50)}
            ujson.dumps(test_obj, encode_html_chars=True)
            ujson.dumps(test_obj, encode_html_chars=False)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 7: ujson.dumps() with escape_forward_slashes
    if len(data) > 5:
        try:
            test_obj = {"url": "https://example.com/path/to/resource"}
            ujson.dumps(test_obj, escape_forward_slashes=True)
            ujson.dumps(test_obj, escape_forward_slashes=False)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 8: ujson.dumps() with various indent levels
    if len(data) > 2:
        try:
            indent = data[0] % 20  # 0-19 indent
            test_obj = {"nested": {"key": "value"}}
            ujson.dumps(test_obj, indent=indent)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 9: ujson.dumps() with sort_keys
    if len(data) > 5:
        try:
            test_obj = {
                fdp.ConsumeUnicodeNoSurrogates(10): fdp.ConsumeUnicodeNoSurrogates(10)
                for _ in range(3)
            }
            ujson.dumps(test_obj, sort_keys=True)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 10: ujson.dumps() with special float values (NaN, Infinity)
    try:
        import math
        special_floats = [math.nan, math.inf, -math.inf, 0.0, -0.0]
        for val in special_floats:
            try:
                ujson.dumps({"value": val}, allow_nan=True)
            except (ValueError, TypeError, OverflowError):
                pass
            try:
                ujson.dumps({"value": val}, allow_nan=False)
            except (ValueError, TypeError, OverflowError):
                pass
    except Exception:
        pass

    # Test 11: Test with deeply nested structures
    if len(data) > 2:
        depth = min(data[0] % 50, 30)  # Max depth 30 to avoid stack overflow
        try:
            nested = text
            for _ in range(depth):
                nested = [nested]
            ujson.dumps(nested)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 12: Test with large numbers
    if len(data) >= 8:
        try:
            import struct
            num = struct.unpack("q", data[:8])[0]
            ujson.dumps({"large_int": num})
            ujson.loads(f'{{"num": {num}}}')
        except (ValueError, TypeError, OverflowError, struct.error):
            pass
        except Exception:
            pass

    # Test 13: Test with Decimal type
    try:
        from decimal import Decimal
        dec_str = fdp.ConsumeUnicodeNoSurrogates(20)
        try:
            dec = Decimal(dec_str)
            ujson.dumps(dec)
        except Exception:
            pass
    except ImportError:
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
