import atheris
import sys
import black

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        black.format_str(s, mode=black.Mode())
    except (black.parsing.InvalidInput, ValueError, tokenize.TokenError, IndentationError):
        pass
    except Exception as e:
        # Some exceptions might be expected if the code is invalid
        # but we want to catch actual crashes in black itself
        if "Cannot parse" in str(e):
            pass
        else:
            print(f"Unexpected exception: {type(e)}: {e}")
            raise e

# Need to import tokenize for the exception
import tokenize
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
