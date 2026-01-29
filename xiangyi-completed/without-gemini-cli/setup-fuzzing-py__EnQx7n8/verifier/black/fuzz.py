import atheris
import sys
import black

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10240))
        black.format_str(s, mode=black.Mode())
    except (black.parsing.InvalidInput, black.parsing.ASTSafetyError, SyntaxError):
        pass
    except Exception as e:
        # We might want to catch other exceptions that are not expected
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
