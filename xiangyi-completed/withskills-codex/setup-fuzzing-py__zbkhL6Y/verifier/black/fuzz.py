import sys
import atheris


def _load():
    with atheris.instrument_imports():
        import black
    return black


black = _load()


def _line_ranges(fdp):
    ranges = []
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        start = fdp.ConsumeIntInRange(1, 500)
        end = fdp.ConsumeIntInRange(1, 500)
        if fdp.ConsumeBool():
            ranges.append(f"{start}")
        else:
            ranges.append(f"{start}-{end}")
    return ranges


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(500)
    if src and not src.endswith("\n"):
        src += "\n"
    mode = black.Mode(line_length=fdp.ConsumeIntInRange(1, 200))

    try:
        choice = fdp.ConsumeIntInRange(0, 6)
        if choice == 0:
            black.format_str(src, mode=mode)
        elif choice == 1:
            black.format_file_contents(src, fast=False, mode=mode)
        elif choice == 2:
            black.format_cell(src, fast=True, mode=mode)
        elif choice == 3:
            black.parsing.parse_ast(src)
        elif choice == 4:
            black.numerics.format_float_or_int_string(src.strip() or "0")
        elif choice == 5:
            black.ranges.parse_line_ranges(_line_ranges(fdp))
        else:
            black.format_ipynb_string(src, fast=True, mode=mode)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
