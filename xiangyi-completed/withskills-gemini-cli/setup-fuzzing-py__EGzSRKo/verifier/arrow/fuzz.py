import sys
import atheris

with atheris.instrument_imports():
    import arrow
    import arrow.parser

def TestOneInput(data):
    try:
        s = data.decode('utf-8')
        arrow.get(s)
    except (UnicodeDecodeError, arrow.parser.ParserError, ValueError, TypeError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
