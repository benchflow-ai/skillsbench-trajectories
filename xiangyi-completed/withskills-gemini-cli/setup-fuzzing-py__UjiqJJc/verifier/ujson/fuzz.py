#!/usr/bin/python3
import atheris
import sys
import os

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        # Fuzz ujson.loads
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError):
        return
    except Exception as e:
        print(f"Unexpected exception: {type(e).__name__}: {e}")
        raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
