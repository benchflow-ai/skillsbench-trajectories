import sys
sys.dont_write_bytecode = True

import atheris
import ujson


def TestOneInput(data: bytes):
    """Fuzz ujson.loads() with raw bytes and optionally test round-trip via ujson.dumps().

    Primary target: ujson.loads() -- the C-level JSON decoder accepting arbitrary
    bytes input. This exercises the full decoder surface including UTF-8 parsing,
    numeric overflow handling, unicode escape sequences, surrogate pairs, deeply
    nested structures, and escape buffer management.

    Secondary target: round-trip consistency via ujson.dumps(ujson.loads(data)),
    verifying that the encoder can handle whatever the decoder produces and that
    the result is itself parseable.
    """
    fdp = atheris.FuzzedDataProvider(data)

    # --- Target 1: ujson.loads with raw bytes ---
    try:
        obj = ujson.loads(data)
    except (ValueError, OverflowError, MemoryError, UnicodeDecodeError, TypeError, RecursionError):
        # These are all expected/acceptable exceptions from the decoder.
        # ValueError includes ujson.JSONDecodeError.
        obj = None
        pass

    # --- Target 1b: ujson.loads with str input (different C code path) ---
    try:
        str_input = data.decode('utf-8', errors='surrogatepass')
        ujson.loads(str_input)
    except (ValueError, OverflowError, MemoryError, UnicodeDecodeError, TypeError, RecursionError):
        pass

    # --- Target 3: Round-trip consistency (loads -> dumps -> loads) ---
    if obj is not None:
        try:
            encoded = ujson.dumps(obj)
            ujson.loads(encoded)
        except (ValueError, OverflowError, MemoryError, UnicodeDecodeError, TypeError, RecursionError):
            pass

    # --- Target 2: ujson.dumps with fuzzed options on a simple constructed object ---
    if fdp.remaining_bytes() >= 4:
        ensure_ascii = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()
        encode_html_chars = fdp.ConsumeBool()
        escape_forward_slashes = fdp.ConsumeBool()

        # Build a small object from remaining fuzzed data for encoder testing
        remaining = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        test_obj = {"key": remaining, "nested": [1, 2.5, True, None, remaining]}

        try:
            result = ujson.dumps(
                test_obj,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
            )
            # Verify encoder output is parseable
            ujson.loads(result)
        except (ValueError, OverflowError, MemoryError, UnicodeDecodeError, TypeError, RecursionError):
            pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
