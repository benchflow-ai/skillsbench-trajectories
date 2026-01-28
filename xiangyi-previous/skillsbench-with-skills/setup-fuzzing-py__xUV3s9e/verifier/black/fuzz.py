import atheris
import sys
import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        black.format_str(fdp.ConsumeString(sys.maxsize), mode=black.Mode())
    except (black.InvalidInput, ValueError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
