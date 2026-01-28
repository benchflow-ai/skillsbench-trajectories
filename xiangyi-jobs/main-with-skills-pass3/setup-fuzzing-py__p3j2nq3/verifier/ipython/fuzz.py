import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


_TM = TransformerManager()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(400)
    if fdp.ConsumeBool():
        cell = "%" + cell
    if fdp.ConsumeBool():
        cell = cell + "\\"
    if fdp.ConsumeBool():
        cell = "\n" + cell

    _safe_call(_TM.transform_cell, cell)
    _safe_call(_TM.check_complete, cell)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
