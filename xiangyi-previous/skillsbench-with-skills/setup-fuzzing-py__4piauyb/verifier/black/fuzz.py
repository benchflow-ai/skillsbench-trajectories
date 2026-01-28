import sys
import atheris
import black
from black import Mode


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(2000)
    line_length = fdp.ConsumeIntInRange(1, 200)
    mode = Mode(line_length=line_length)
    try:
        black.format_str(src, mode=mode)
    except Exception:
        pass
    try:
        black.format_file_contents(src, fast=True, mode=mode)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
