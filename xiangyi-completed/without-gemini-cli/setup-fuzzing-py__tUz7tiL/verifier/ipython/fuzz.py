import atheris
import sys
import os

with atheris.instrument_imports():
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.inputtransformer2 import TransformerManager

# Initialize InteractiveShell once
shell = InteractiveShell()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz run_cell
        code = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        # We use silent=True to avoid too much output and side effects
        shell.run_cell(code, store_history=False, silent=True)
    except Exception:
        # Most exceptions are caught by run_cell itself, but just in case
        pass

if __name__ == "__main__":
    # Disable history and other things that might be slow or problematic
    os.environ["IPYTHONDIR"] = "/tmp/ipython_fuzz"
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
