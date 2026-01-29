import atheris
import sys
import os

# Set up RegEx hooks before importing arrow
atheris.enabled_hooks.add("RegEx")

with atheris.instrument_imports():
    import arrow
    from arrow.parser import ParserError, ParserMatchError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        
        # Test arrow.get(str)
        try:
            arrow.get(s)
        except (ParserError, ParserMatchError, ValueError, TypeError):
            pass
        
        # Test arrow.get(str, format)
        fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        try:
            arrow.get(s, fmt)
        except (ParserError, ParserMatchError, ValueError, TypeError):
            pass

        # Test arrow.get(str, list of formats)
        fmt_list = [fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50)) for _ in range(fdp.ConsumeIntInRange(0, 5))]
        try:
            arrow.get(s, fmt_list)
        except (ParserError, ParserMatchError, ValueError, TypeError):
            pass
            
    except Exception:
        # Unexpected exception - let Atheris catch it
        raise

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
