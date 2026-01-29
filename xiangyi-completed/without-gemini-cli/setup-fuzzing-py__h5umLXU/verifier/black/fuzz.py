import atheris
import sys
import black

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        black.format_str(s, mode=black.Mode())
    except (black.parsing.InvalidInput, ValueError, SyntaxError, black.parsing.TokenError):
        pass
    except Exception as e:
        # We might want to catch other specific exceptions that are expected
        # but for now let's focus on unexpected crashes
        if "Cannot parse" in str(e):
            pass
        else:
            raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
