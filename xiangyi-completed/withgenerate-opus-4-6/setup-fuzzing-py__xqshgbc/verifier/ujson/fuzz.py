"""Coverage-guided fuzz driver for UltraJSON (ujson)."""
import atheris
import sys
from io import StringIO, BytesIO

# Use instrument_all() for C extension coverage
atheris.instrument_all()
import ujson


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz ujson.loads() with raw string input
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        try:
            ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError, TypeError,
                OverflowError, RecursionError):
            pass

    elif choice == 1:
        # Fuzz ujson.loads() with raw bytes input
        b = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
        try:
            ujson.loads(b)
        except (ujson.JSONDecodeError, ValueError, TypeError,
                OverflowError, RecursionError, UnicodeDecodeError):
            pass

    elif choice == 2:
        # Fuzz ujson.dumps() with random generated objects
        obj = _build_random_json(fdp, depth=4)
        ensure_ascii = fdp.ConsumeBool()
        encode_html_chars = fdp.ConsumeBool()
        escape_forward_slashes = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()
        indent = fdp.ConsumeIntInRange(0, 8)
        try:
            encoded = ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                sort_keys=sort_keys,
                indent=indent,
            )
            # Roundtrip test: verify decode(encode(obj)) works
            ujson.loads(encoded)
        except (ujson.JSONDecodeError, ValueError, TypeError,
                OverflowError, RecursionError):
            pass

    elif choice == 3:
        # Fuzz ujson.load() with BytesIO
        b = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 512))
        try:
            ujson.load(BytesIO(b))
        except (ujson.JSONDecodeError, ValueError, TypeError,
                OverflowError, RecursionError, UnicodeDecodeError,
                AttributeError):
            pass


def _build_random_json(fdp, depth):
    """Build a random JSON-serializable Python object."""
    if depth <= 0 or fdp.remaining_bytes() < 4:
        t = fdp.ConsumeIntInRange(0, 5)
        if t == 0:
            return fdp.ConsumeIntInRange(-2**31, 2**31 - 1)
        elif t == 1:
            return fdp.ConsumeRegularFloat()
        elif t == 2:
            return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        elif t == 3:
            return None
        elif t == 4:
            return fdp.ConsumeBool()
        else:
            return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 16))

    container_type = fdp.ConsumeIntInRange(0, 1)
    size = fdp.ConsumeIntInRange(0, 5)
    if container_type == 0:
        return [_build_random_json(fdp, depth - 1) for _ in range(size)]
    else:
        return {
            fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 16)):
                _build_random_json(fdp, depth - 1)
            for _ in range(size)
        }


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
