import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)

    if choice == 0:
        # Fuzz ujson.loads with string input
        try:
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
            pass
    elif choice == 1:
        # Fuzz ujson.loads with bytes input
        try:
            b = fdp.ConsumeBytes(fdp.remaining_bytes())
            ujson.loads(b)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError, UnicodeDecodeError):
            pass
    else:
        # Round-trip: loads then dumps
        try:
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            obj = ujson.loads(s)
            ujson.dumps(obj)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
            pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
