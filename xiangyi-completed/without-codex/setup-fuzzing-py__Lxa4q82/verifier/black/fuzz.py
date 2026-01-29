import sys
import atheris

with atheris.instrument_imports():
    import black
    from tokenize import TokenError


def _fuzz_format_str(fdp: atheris.FuzzedDataProvider) -> None:
    text = fdp.ConsumeUnicodeNoSurrogates(256)
    mode = black.Mode()
    black.format_str(text, mode=mode)


def _fuzz_bytes_roundtrip(fdp: atheris.FuzzedDataProvider) -> None:
    data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))
    mode = black.Mode()
    src, _enc, _nl = black.decode_bytes(data, mode=mode)
    black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)


def _fuzz_ipynb(fdp: atheris.FuzzedDataProvider) -> None:
    text = fdp.ConsumeUnicodeNoSurrogates(512)
    black.format_ipynb_string(text, fast=fdp.ConsumeBool(), mode=black.Mode())


def _fuzz_line_ranges(fdp: atheris.FuzzedDataProvider) -> None:
    ranges = [
        fdp.ConsumeUnicodeNoSurrogates(16),
        fdp.ConsumeUnicodeNoSurrogates(16),
    ]
    black.parse_line_ranges(ranges)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            _fuzz_format_str(fdp)
        elif choice == 1:
            _fuzz_bytes_roundtrip(fdp)
        elif choice == 2:
            _fuzz_ipynb(fdp)
        else:
            _fuzz_line_ranges(fdp)
    except (
        black.InvalidInput,
        black.NothingChanged,
        SyntaxError,
        IndentationError,
        TokenError,
        ValueError,
        TypeError,
        AssertionError,
    ):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
