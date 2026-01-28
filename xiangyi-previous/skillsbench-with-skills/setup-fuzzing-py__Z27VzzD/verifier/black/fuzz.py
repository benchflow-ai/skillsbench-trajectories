import atheris
import sys
with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
