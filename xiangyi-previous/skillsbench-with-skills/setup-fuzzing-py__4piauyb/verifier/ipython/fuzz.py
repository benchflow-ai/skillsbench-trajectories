import sys
import atheris
import ast
from IPython.core.inputtransformer2 import TransformerManager


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(500)
    tm = TransformerManager()
    transformed = None
    try:
        transformed = tm.transform_cell(cell)
    except Exception:
        pass
    try:
        tm.check_complete(cell)
    except Exception:
        pass
    if transformed:
        try:
            ast.parse(transformed)
        except Exception:
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
