import sys
import atheris
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return
    
    try:
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass
    except Exception as e:
        # Catching other potential exceptions to see if we find anything interesting,
        # but normally we'd want to be specific. 
        # For now, let's catch standard parsing issues.
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
