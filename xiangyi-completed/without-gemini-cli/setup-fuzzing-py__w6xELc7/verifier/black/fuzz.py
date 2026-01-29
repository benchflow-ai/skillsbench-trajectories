import sys
import atheris
import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return
    
    try:
        black.format_str(s, mode=black.Mode())
    except black.InvalidInput:
        pass
    except Exception:
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
