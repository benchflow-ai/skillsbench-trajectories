import sys

import atheris

with atheris.instrument_imports():
    from IPython.core import splitinput
    from IPython.core.inputtransformer2 import TransformerManager


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(2048)

    try:
        splitinput.split_user_input(text)
        transformer = TransformerManager()
        transformer.transform_cell(text)
    except (AssertionError, RuntimeError, SyntaxError, ValueError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
