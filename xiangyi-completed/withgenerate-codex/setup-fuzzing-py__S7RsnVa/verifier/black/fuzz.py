import sys

import atheris

import black
from black import parsing as black_parsing
from black import ranges as black_ranges


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)
    line_length = fdp.ConsumeIntInRange(1, 120)
    mode = black.Mode(line_length=line_length)

    try:
        black.format_str(text, mode=mode)
    except (black.InvalidInput, SyntaxError, ValueError):
        pass

    # Parse line ranges (best-effort)
    range_text = fdp.ConsumeUnicodeNoSurrogates(40)
    try:
        black_ranges.parse_line_ranges([range_text])
    except ValueError:
        pass

    # Direct parsing APIs
    try:
        black_parsing.lib2to3_parse(text)
    except (black.InvalidInput, SyntaxError, ValueError):
        pass

    try:
        black_parsing.parse_ast(text)
    except (black.InvalidInput, SyntaxError, ValueError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
