import sys

import atheris

with atheris.instrument_imports():
    import black


def _mode_from_fdp(fdp: atheris.FuzzedDataProvider) -> black.Mode:
    return black.Mode(
        line_length=fdp.ConsumeIntInRange(40, 200),
        string_normalization=fdp.ConsumeBool(),
        magic_trailing_comma=fdp.ConsumeBool(),
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(4096)
    mode = _mode_from_fdp(fdp)

    try:
        if fdp.ConsumeBool():
            black.format_str(text, mode=mode)
        else:
            black.format_file_contents(text, fast=fdp.ConsumeBool(), mode=mode)
    except (
        black.ASTSafetyError,
        black.InvalidInput,
        black.NothingChanged,
        SyntaxError,
        ValueError,
    ):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
