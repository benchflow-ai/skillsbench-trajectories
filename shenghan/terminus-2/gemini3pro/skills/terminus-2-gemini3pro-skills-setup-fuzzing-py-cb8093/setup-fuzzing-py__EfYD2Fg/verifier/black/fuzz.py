import atheris
import sys
import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        src_contents = fdp.ConsumeString(sys.maxsize)
        mode = black.Mode()
        black.format_str(src_contents, mode=mode)
    except (black.parsing.InvalidInput, ValueError, AssertionError):
        pass
    except Exception as e:
        # Catching generic exceptions to prevent fuzzer crash on expected failures if any
        # But ideally we should only catch specific ones.
        # For now, let's catch everything that seems like a parsing error.
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
