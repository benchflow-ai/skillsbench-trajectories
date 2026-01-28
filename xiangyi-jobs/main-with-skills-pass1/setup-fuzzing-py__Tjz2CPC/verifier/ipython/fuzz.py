import atheris
import sys

with atheris.instrument_imports():
    from IPython.core import inputtransformer2, splitinput, magic_arguments, magic


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(400)
    tm = inputtransformer2.TransformerManager()
    try:
        if fdp.ConsumeBool():
            tm.transform_cell(cell)
        else:
            tm.check_complete(cell)
        if fdp.ConsumeBool():
            splitinput.split_user_input(cell)
        if fdp.ConsumeBool():
            magic_arguments.parse_argstring(lambda: None, cell)
        if fdp.ConsumeBool():
            magic.Magics(None).parse_options(cell, "a:b")
    except (SyntaxError, ValueError, RuntimeError, TypeError):
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
