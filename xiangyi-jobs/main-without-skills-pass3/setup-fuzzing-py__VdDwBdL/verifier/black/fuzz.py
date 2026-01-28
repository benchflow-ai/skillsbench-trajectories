import sys

import atheris
import black


def _consume_text(fdp, max_len: int) -> str:
    return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, max_len))


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    source = _consume_text(fdp, 2000)
    line_length = fdp.ConsumeIntInRange(40, 200)
    string_normalization = fdp.ConsumeIntInRange(0, 1) == 1

    mode = black.Mode(line_length=line_length, string_normalization=string_normalization)

    try:
        black.format_str(source, mode=mode)
    except (black.InvalidInput, SyntaxError, ValueError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
