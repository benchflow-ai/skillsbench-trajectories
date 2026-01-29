#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for ujson (UltraJSON) library.
Uses Atheris for LibFuzzer-style fuzzing.

This is a high-priority fuzz target as ujson is a C extension
that handles untrusted JSON input.
"""
import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for ujson JSON parsing."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import ujson inside the function for instrumentation
    import ujson

    # Test 1: ujson.loads() with bytes input
    try:
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            ujson.JSONDecodeError):
        pass
    except Exception as e:
        # Catch any other JSON-related errors
        if "JSON" in type(e).__name__ or "Decode" in type(e).__name__:
            pass
        else:
            raise

    # Test 2: ujson.loads() with string input
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(4096)
        if json_string:
            ujson.loads(json_string)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            ujson.JSONDecodeError):
        pass
    except Exception as e:
        if "JSON" in type(e).__name__ or "Decode" in type(e).__name__:
            pass
        else:
            raise

    # Test 3: ujson.decode() (alias for loads)
    try:
        ujson.decode(data)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            ujson.JSONDecodeError):
        pass
    except Exception as e:
        if "JSON" in type(e).__name__ or "Decode" in type(e).__name__:
            pass
        else:
            raise

    # Test 4: Roundtrip test - parse then serialize
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(1024)
        if json_string:
            obj = ujson.loads(json_string)
            # Try to re-serialize
            ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            ujson.JSONDecodeError, RecursionError):
        pass
    except Exception as e:
        if "JSON" in type(e).__name__ or "Decode" in type(e).__name__:
            pass
        else:
            raise

    # Test 5: ujson.dumps with various options
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(512)
        if json_string:
            obj = ujson.loads(json_string)
            indent = fdp.ConsumeIntInRange(0, 10)
            ensure_ascii = fdp.ConsumeBool()
            encode_html_chars = fdp.ConsumeBool()
            escape_forward_slashes = fdp.ConsumeBool()
            ujson.dumps(obj,
                       indent=indent,
                       ensure_ascii=ensure_ascii,
                       encode_html_chars=encode_html_chars,
                       escape_forward_slashes=escape_forward_slashes)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            ujson.JSONDecodeError, RecursionError):
        pass
    except Exception as e:
        if "JSON" in type(e).__name__ or "Decode" in type(e).__name__:
            pass
        else:
            raise


def main():
    # Note: ujson is a C extension, atheris instrumentation won't provide
    # coverage for the C code, but it will track Python-level coverage
    # and can still find crashes in the C extension
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
