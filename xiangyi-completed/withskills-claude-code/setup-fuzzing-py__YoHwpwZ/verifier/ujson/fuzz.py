#!/usr/bin/env python3
"""
Atheris-based fuzzer for UltraJSON (ujson)
Targets: ujson.loads() - JSON deserialization (C extension, high priority)
"""

import sys
import atheris

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for ujson JSON parsing"""
    if len(data) == 0:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test ujson.loads() with various inputs
    # This is critical as it's a C extension parsing untrusted input

    # Test with bytes
    try:
        json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, fdp.remaining_bytes()))
        if json_bytes:
            parsed = ujson.loads(json_bytes)
            # If parsing succeeded, try to serialize back
            if parsed is not None:
                serialized = ujson.dumps(parsed)
    except (ValueError, OverflowError, TypeError):
        # Expected exceptions
        pass
    except Exception as e:
        # Filter expected exceptions
        exc_name = type(e).__name__
        if exc_name not in ['JSONDecodeError']:
            raise

    # Test with unicode string
    remaining = fdp.remaining_bytes()
    if remaining > 0:
        try:
            json_string = fdp.ConsumeUnicodeNoSurrogates(remaining)
            if json_string:
                parsed = ujson.loads(json_string)
                if parsed is not None:
                    # Test dumps with various options
                    ujson.dumps(parsed, ensure_ascii=fdp.ConsumeBool())
        except (ValueError, OverflowError, TypeError, RecursionError):
            # Expected exceptions
            pass
        except Exception as e:
            exc_name = type(e).__name__
            if exc_name not in ['JSONDecodeError', 'MemoryError']:
                raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
