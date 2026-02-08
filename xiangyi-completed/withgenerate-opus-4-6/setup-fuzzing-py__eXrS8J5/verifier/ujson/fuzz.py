import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    # Fuzz ujson.loads (decode)
    try:
        obj = ujson.loads(text)
        # Roundtrip test: encode the decoded object back
        try:
            encoded = ujson.dumps(obj)
            ujson.loads(encoded)
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
            pass
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Fuzz ujson.loads with bytes input
    try:
        raw_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())
        if raw_bytes:
            ujson.loads(raw_bytes)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Fuzz ujson.dumps with various options
    try:
        ujson.dumps(text, ensure_ascii=fdp.ConsumeBool(),
                    encode_html_chars=fdp.ConsumeBool(),
                    escape_forward_slashes=fdp.ConsumeBool())
    except (ValueError, TypeError, OverflowError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
