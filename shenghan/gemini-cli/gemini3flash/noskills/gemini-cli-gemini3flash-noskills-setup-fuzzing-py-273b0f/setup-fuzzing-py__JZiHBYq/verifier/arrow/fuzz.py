import atheris
import sys
import arrow

with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    input_str = fdp.ConsumeUnicodeNoSurrogates(1024)
    try:
        arrow.get(input_str)
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass
    except Exception as e:
        # We might want to catch other expected exceptions or report unexpected ones
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
