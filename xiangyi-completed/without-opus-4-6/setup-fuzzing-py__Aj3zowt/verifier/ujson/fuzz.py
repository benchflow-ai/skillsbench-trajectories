"""Coverage-guided fuzzer for UltraJSON using atheris + LibFuzzer."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for ujson's encode/decode functions."""
    fdp = atheris.FuzzedDataProvider(data)

    import ujson

    # Fuzz ujson.loads (decode) - PRIMARY target
    json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    if not json_str:
        return

    try:
        result = ujson.loads(json_str)
        # Round-trip: if decode succeeds, encode the result back
        try:
            ujson.dumps(result)
        except Exception:
            pass
    except (ujson.JSONDecodeError, ValueError, OverflowError):
        pass
    except Exception:
        pass

    # Fuzz ujson.loads with bytes input
    json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
    try:
        ujson.loads(json_bytes)
    except Exception:
        pass

    # Fuzz ujson.dumps with various options
    try:
        obj = ujson.loads(json_str)
        ensure_ascii = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()
        encode_html = fdp.ConsumeBool()
        escape_fwd = fdp.ConsumeBool()
        indent_val = fdp.ConsumeIntInRange(0, 10)
        ujson.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            encode_html_chars=encode_html,
            escape_forward_slashes=escape_fwd,
            indent=indent_val,
        )
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
