import sys

import atheris

with atheris.instrument_imports():
    import black
    from black import parsing
    from black import ranges


def _make_ranges(fdp):
    count = fdp.ConsumeIntInRange(0, 5)
    result = []
    for _ in range(count):
        start = fdp.ConsumeIntInRange(1, 200)
        end = fdp.ConsumeIntInRange(start, start + 200)
        result.append(f"{start}-{end}")
    return result


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(4000)
    line_length = fdp.ConsumeIntInRange(1, 200)
    mode = black.Mode(line_length=line_length)

    try:
        black.format_str(src, mode=mode)
    except (black.InvalidInput, SyntaxError, ValueError, TypeError):
        pass

    try:
        parsing.parse_ast(src)
    except (SyntaxError, ValueError, TypeError, MemoryError):
        pass

    try:
        parsing.lib2to3_parse(src)
    except (SyntaxError, ValueError, TypeError):
        pass

    try:
        ranges.parse_line_ranges(_make_ranges(fdp))
    except (ValueError, TypeError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
