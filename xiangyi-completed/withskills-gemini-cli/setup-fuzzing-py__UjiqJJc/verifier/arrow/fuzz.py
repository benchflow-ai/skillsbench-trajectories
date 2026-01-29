#!/usr/bin/python3
import atheris
import sys
import os

with atheris.instrument_imports():
    import arrow
    from arrow.parser import ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            # Fuzz parsing a string
            s = fdp.ConsumeUnicode(100)
            arrow.get(s)
        elif choice == 1:
            # Fuzz parsing a string with format
            s = fdp.ConsumeUnicode(100)
            fmt = fdp.ConsumeUnicode(100)
            arrow.get(s, fmt)
        elif choice == 2:
            # Fuzz timestamp
            t = fdp.ConsumeFloat()
            arrow.get(t)
        elif choice == 3:
            # Fuzz multiple args (e.g. year, month, day...)
            # We'll just try a few
            args = []
            for _ in range(fdp.ConsumeIntInRange(1, 6)):
                args.append(fdp.ConsumeIntInRange(1, 3000))
            arrow.get(*args)

    except (ParserError, ValueError, TypeError, OverflowError):
        return
    except Exception as e:
        # Unexpected exceptions
        print(f"Unexpected exception: {type(e).__name__}: {e}")
        raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
