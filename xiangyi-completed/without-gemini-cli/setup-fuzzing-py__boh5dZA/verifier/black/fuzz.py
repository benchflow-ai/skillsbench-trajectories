import atheris
import sys

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10240))
        black.format_str(src, mode=black.Mode())
    except black.parsing.InvalidInput:
        pass
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()