"""Coverage-guided fuzz driver for the IPython library.

Targets:
- TransformerManager.transform_cell() - main input transformation pipeline
- TransformerManager.check_complete() - code completeness validation
- split_user_input() - input line parsing
"""
import sys
import atheris

# Use instrument_all() instead of instrument_imports() to avoid
# instrumenting the large IPython dependency tree during import
atheris.instrument_all()

from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input

_tm = TransformerManager()


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    try:
        if choice == 0:
            _tm.transform_cell(text)
        elif choice == 1:
            _tm.check_complete(text)
        else:
            split_user_input(text)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
