import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    
    # Fuzz loads
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes() // 2)
        try:
            ujson.loads(s)
        except (ValueError, OverflowError):
            pass
    except Exception:
        raise

    # Fuzz dumps
    # Since we need an object to dump, and ujson.loads(s) might return one,
    # we can use that.
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            obj = ujson.loads(s)
            ujson.dumps(obj)
        except (ValueError, OverflowError):
            pass
    except Exception:
        raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
