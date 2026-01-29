import sys
import tempfile

import atheris
import black
from black import files as black_files
from black import ranges as black_ranges


_MAX_TEXT = 4096


def _make_mode(fdp: atheris.FuzzedDataProvider) -> black.Mode:
    return black.Mode(
        line_length=fdp.ConsumeIntInRange(1, 200),
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_TEXT, fdp.remaining_bytes()))
    mode = _make_mode(fdp)

    if text:
        try:
            black.format_str(text, mode=mode)
        except Exception:
            pass

        try:
            black.format_file_contents(text, fast=fdp.ConsumeBool(), mode=mode)
        except Exception:
            pass

        try:
            black.assert_equivalent(text, text)
        except Exception:
            pass

    blob = fdp.ConsumeBytes(min(2048, fdp.remaining_bytes()))
    if blob:
        try:
            black.decode_bytes(blob, mode=mode)
        except Exception:
            pass

    ranges = []
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        start = fdp.ConsumeIntInRange(1, 200)
        end = fdp.ConsumeIntInRange(1, 200)
        ranges.append(f"{start}-{end}")
    if ranges:
        try:
            black_ranges.parse_line_ranges(ranges)
        except Exception:
            pass

    if text:
        try:
            with tempfile.NamedTemporaryFile("w+", suffix=".toml", delete=True) as tmp:
                tmp.write(text)
                tmp.flush()
                black_files.parse_pyproject_toml(tmp.name)
        except Exception:
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
