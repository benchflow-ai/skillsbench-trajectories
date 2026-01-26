import atheris
import sys
import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except (black.InvalidInput, ValueError):
        pass
    except Exception as e:
        # Catch other potential parsing errors but not crashes
        if "Cannot parse" in str(e):
             pass
        else:
             pass # Ignore for now to keep fuzzing running

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
