#!/usr/bin/python3
import atheris
import sys
import os
import io
from contextlib import redirect_stdout, redirect_stderr

with atheris.instrument_imports():
    from IPython.core.interactiveshell import InteractiveShell

# Initialize InteractiveShell once
shell = InteractiveShell()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz the cell content
        raw_cell = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        
        # We redirect stdout/stderr to avoid noise
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            shell.run_cell(raw_cell, store_history=False, silent=True)

    except Exception as e:
        # Since we are running arbitrary code, many exceptions are expected.
        # However, internal IPython crashes might still be interesting.
        # For now, we just catch everything to keep the fuzzer running.
        return

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
