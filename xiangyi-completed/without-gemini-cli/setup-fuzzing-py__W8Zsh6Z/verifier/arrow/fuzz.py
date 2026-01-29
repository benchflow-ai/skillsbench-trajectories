import atheris
import sys
with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        # Test arrow.get
        try:
            arrow.get(s)
        except Exception:
            pass
        
        # Test parser
        parser = arrow.parser.DateTimeParser()
        try:
            parser.parse_iso(s)
        except Exception:
            pass
            
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
