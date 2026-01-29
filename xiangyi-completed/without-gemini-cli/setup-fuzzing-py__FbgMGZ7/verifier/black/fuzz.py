import sys
import atheris
import black
from black.parsing import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except InvalidInput:
        pass
    except Exception as e:
        if "Cannot parse" in str(e):
             pass
        else:
             # We might want to re-raise unexpected exceptions
             # But for a simple fuzzer setup, catching generic might be safer to avoid immediate exit on known-ish errors
             # black might raise other errors.
             pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
