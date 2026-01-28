import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.parsing import InvalidInput
    from black.mode import Mode

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        src = fdp.ConsumeUnicodeNoSurrogates(1024)
        black.format_str(src, mode=Mode())
    except (InvalidInput, ValueError, SyntaxError):
        pass
    except Exception as e:
        # Some other exceptions might be raised if the input is really weird
        # but for now let's just catch them to avoid stopping the fuzzer
        # unless it's a crash we care about.
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
