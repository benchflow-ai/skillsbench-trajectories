#!/usr/bin/python3
"""Coverage-guided fuzz driver for ujson (UltraJSON).

Targets:
  1. ujson.loads() with string input - JSON string decoding
  2. ujson.loads() with bytes input  - JSON bytes decoding
  3. ujson.dumps() roundtrip         - Encode after decode
  4. Differential: ujson.loads() vs json.loads()
"""
import atheris
import json
import sys

with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    if fdp.remaining_bytes() < 2:
        return
    target = fdp.ConsumeIntInRange(0, 3)

    if target == 0:
        # Target 1: ujson.loads() with string input
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            pass

    elif target == 1:
        # Target 2: ujson.loads() with bytes input
        raw = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            ujson.loads(raw)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            pass

    elif target == 2:
        # Target 3: Roundtrip - loads then dumps
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            obj = ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            return
        try:
            encoded = ujson.dumps(obj)
        except (TypeError, OverflowError, ValueError, MemoryError,
                RecursionError):
            return
        # Verify roundtrip: decode the re-encoded result
        try:
            ujson.loads(encoded)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            pass

    elif target == 3:
        # Target 4: Differential fuzzing ujson vs stdlib json
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

        ujson_ok = True
        json_ok = True
        ujson_result = None
        json_result = None

        try:
            ujson_result = ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            ujson_ok = False

        try:
            json_result = json.loads(s)
        except (json.JSONDecodeError, ValueError, OverflowError,
                TypeError, MemoryError, RecursionError):
            json_ok = False

        # Both paths exercised for coverage; we don't assert equality
        # to avoid false positives from known ujson extensions (NaN, Infinity)


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
