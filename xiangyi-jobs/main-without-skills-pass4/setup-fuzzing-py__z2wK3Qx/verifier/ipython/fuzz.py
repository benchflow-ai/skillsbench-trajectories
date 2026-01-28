import sys

import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input


TRANSFORMER = TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(400)
    line = fdp.ConsumeUnicodeNoSurrogates(200)
    try:
        split_user_input(line)
        TRANSFORMER.transform_cell(cell)
        TRANSFORMER.check_complete(cell)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
