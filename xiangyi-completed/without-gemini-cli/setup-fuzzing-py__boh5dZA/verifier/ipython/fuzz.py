import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.interactiveshell import InteractiveShell

# Initialize InteractiveShell once
shell = InteractiveShell()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10240))
        shell.run_cell(code)
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()