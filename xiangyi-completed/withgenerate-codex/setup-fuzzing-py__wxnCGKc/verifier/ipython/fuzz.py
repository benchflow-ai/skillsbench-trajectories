import sys

import atheris

with atheris.instrument_imports():
    from IPython.core import inputtransformer2


EXPECTED = (
    SyntaxError,
    ValueError,
    RuntimeError,
    TypeError,
)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(4096)
    try:
        manager = inputtransformer2.TransformerManager()
        manager.transform_cell(cell)
        manager.check_complete(cell)
    except EXPECTED:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
