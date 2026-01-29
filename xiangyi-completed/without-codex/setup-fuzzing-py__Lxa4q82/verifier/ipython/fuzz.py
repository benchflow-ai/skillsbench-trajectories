import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.splitinput import LineInfo, split_user_input
    from IPython.utils._process_common import arg_split
    from IPython.utils.text import format_screen


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(256)
    if not text:
        return
    try:
        split_user_input(text)
        LineInfo(text)
        arg_split(text, posix=fdp.ConsumeBool(), strict=fdp.ConsumeBool())
        format_screen(text)
    except ValueError:
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
