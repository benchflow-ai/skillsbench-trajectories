import sys

import atheris
from atheris import FuzzedDataProvider

import black


def TestOneInput(data: bytes) -> None:
    fdp = FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(512)

    mode = black.FileMode()

    try:
        black.format_str(src, mode=mode)
    except (black.InvalidInput, black.NothingChanged, SyntaxError, ValueError):
        pass

    try:
        black.format_file_contents(src, fast=True, mode=mode)
    except (black.InvalidInput, black.NothingChanged, SyntaxError, ValueError):
        pass

    try:
        black.parsing.parse_ast(src)
    except (SyntaxError, ValueError):
        pass

    ranges = []
    for _ in range(fdp.ConsumeIntInRange(0, 3)):
        ranges.append(fdp.ConsumeUnicodeNoSurrogates(16))
    try:
        black.ranges.parse_line_ranges(ranges)
    except (ValueError, TypeError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
