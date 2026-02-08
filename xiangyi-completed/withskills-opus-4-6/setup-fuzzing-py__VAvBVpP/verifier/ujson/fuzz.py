"""
LibFuzzer-based fuzz driver for ujson using atheris.

This fuzzer targets both the decoder (ujson.loads) and encoder (ujson.dumps)
of the ujson C extension library. The decoder is the HIGHEST priority target
because it directly processes untrusted input and is written in C with manual
memory management.

The existing fuzzer at tests/fuzz.py only tests the encoder. This fuzzer
fills the critical gap by focusing on the decoder with arbitrary bytes/string
input, and also tests encode-decode round-trips and encoder options.

Usage:
    python fuzz.py                     # Run with LibFuzzer
    python fuzz.py corpus/             # Run with a corpus directory
    python fuzz.py -max_len=65536      # Limit input size
"""

import atheris
import sys

with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # -------------------------------------------------------------------------
    # HARNESS 1: Decode arbitrary bytes (HIGHEST PRIORITY)
    # Directly exercises the C decoder with untrusted input. This is the most
    # likely entry point for a real-world attack. Tests buffer handling,
    # UTF-8 validation, escape sequence parsing, numeric parsing, and
    # recursive descent through nested structures.
    # -------------------------------------------------------------------------
    fuzz_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 4096))
    try:
        ujson.loads(fuzz_bytes)
    except (ValueError, TypeError, UnicodeDecodeError, UnicodeEncodeError):
        pass

    # -------------------------------------------------------------------------
    # HARNESS 2: Decode bytearray (HIGH PRIORITY)
    # Tests the buffer protocol path in JSONToObj(). bytearray uses the same
    # C code path as bytes but through a different Python type, which could
    # expose buffer lifetime or reference counting issues.
    # -------------------------------------------------------------------------
    try:
        ujson.loads(bytearray(fuzz_bytes))
    except (ValueError, TypeError, UnicodeDecodeError, UnicodeEncodeError):
        pass

    # -------------------------------------------------------------------------
    # HARNESS 3: Decode arbitrary string (HIGH PRIORITY)
    # Exercises the str -> UTF-8 -> C parser path. Uses a different code path
    # in JSONToObj() (PyUnicode_AsEncodedString) compared to bytes input.
    # ConsumeUnicodeNoSurrogates avoids surrogates that would cause
    # UnicodeEncodeError before reaching the C decoder.
    # -------------------------------------------------------------------------
    fuzz_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 4096))
    try:
        ujson.loads(fuzz_string)
    except (ValueError, TypeError, UnicodeDecodeError, UnicodeEncodeError):
        pass

    # -------------------------------------------------------------------------
    # HARNESS 4: Encode-decode round-trip (HIGH PRIORITY)
    # If the decoder successfully parses fuzz_bytes, re-encode the result
    # with ujson.dumps(). This tests both encoder and decoder, and can find
    # inconsistencies, memory corruption, or reference counting bugs that
    # only manifest in round-trip scenarios.
    # -------------------------------------------------------------------------
    try:
        decoded = ujson.loads(fuzz_bytes)
        ujson.dumps(decoded)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            UnicodeEncodeError, RecursionError):
        pass

    # -------------------------------------------------------------------------
    # HARNESS 5: Encode with various options (MEDIUM PRIORITY)
    # Exercises different encoder code paths: ASCII escaping, HTML char
    # encoding, indentation with buffer growth, sorted key iteration,
    # and forward slash escaping. Each option triggers different buffer
    # management and string escaping logic in the C encoder.
    # -------------------------------------------------------------------------
    ensure_ascii = fdp.ConsumeBool()
    encode_html_chars = fdp.ConsumeBool()
    sort_keys = fdp.ConsumeBool()
    escape_forward_slashes = fdp.ConsumeBool()
    indent = fdp.ConsumeIntInRange(0, 20)

    try:
        decoded = ujson.loads(fuzz_bytes)
        ujson.dumps(
            decoded,
            ensure_ascii=ensure_ascii,
            encode_html_chars=encode_html_chars,
            sort_keys=sort_keys,
            escape_forward_slashes=escape_forward_slashes,
            indent=indent,
        )
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
            UnicodeEncodeError, RecursionError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
