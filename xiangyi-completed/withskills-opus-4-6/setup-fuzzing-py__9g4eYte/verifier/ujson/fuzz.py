"""Coverage-guided fuzz driver for ujson using Atheris (LibFuzzer)."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for ujson's JSON parsing and encoding functions."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        import ujson
    except ImportError:
        return

    # Fuzz ujson.loads with string input - primary attack surface
    json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    try:
        ujson.loads(json_str)
    except (ujson.JSONDecodeError, ValueError, OverflowError, MemoryError):
        pass

    # Fuzz ujson.loads with raw bytes input - exercises buffer protocol path
    json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
    try:
        ujson.loads(json_bytes)
    except (ujson.JSONDecodeError, ValueError, OverflowError, MemoryError):
        pass

    # Fuzz ujson.dumps with various option combinations
    try:
        obj = ujson.loads(json_str)
        ensure_ascii = fdp.ConsumeBool()
        encode_html = fdp.ConsumeBool()
        escape_fwd = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()
        indent_val = fdp.ConsumeIntInRange(0, 16)
        ujson.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            encode_html_chars=encode_html,
            escape_forward_slashes=escape_fwd,
            sort_keys=sort_keys,
            indent=indent_val,
        )
    except Exception:
        pass

    # Fuzz round-trip: loads -> dumps -> loads
    try:
        parsed = ujson.loads(json_str)
        encoded = ujson.dumps(parsed)
        ujson.loads(encoded)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
