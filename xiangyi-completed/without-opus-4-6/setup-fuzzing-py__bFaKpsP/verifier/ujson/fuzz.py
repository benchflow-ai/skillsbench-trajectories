"""Coverage-guided fuzzer for UltraJSON (ujson) library."""

import sys
import atheris


def TestOneInput(data):
    """Fuzz target for ujson's decode and encode functions."""
    fdp = atheris.FuzzedDataProvider(data)

    import ujson

    # Fuzz ujson.loads with string input
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    if text:
        try:
            result = ujson.loads(text)
            # Roundtrip: encode the decoded result back
            ujson.dumps(result)
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass

    # Fuzz ujson.loads with bytes input
    raw_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 512))
    if raw_bytes:
        try:
            result = ujson.loads(raw_bytes)
            ujson.dumps(result)
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass

    # Fuzz ujson.dumps with various encoding options
    if text:
        try:
            decoded = ujson.loads(text)
            ujson.dumps(decoded, ensure_ascii=fdp.ConsumeBool())
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass
        try:
            decoded = ujson.loads(text)
            ujson.dumps(decoded, encode_html_chars=True)
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass
        try:
            decoded = ujson.loads(text)
            indent = fdp.ConsumeIntInRange(0, 8)
            ujson.dumps(decoded, indent=indent)
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass
        try:
            decoded = ujson.loads(text)
            ujson.dumps(decoded, sort_keys=True)
        except (ValueError, OverflowError, TypeError, ujson.JSONDecodeError):
            pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
