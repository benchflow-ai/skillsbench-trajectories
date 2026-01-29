import atheris
import sys

import black


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    length = fdp.ConsumeIntInRange(0, 4096)
    src = fdp.ConsumeUnicodeNoSurrogates(length)

    mode = black.Mode(
        line_length=fdp.ConsumeIntInRange(20, 200),
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
    )

    try:
        black.format_str(src, mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        black.ASTSafetyError,
        SyntaxError,
        ValueError,
    ):
        pass

    try:
        black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)
    except (
        black.InvalidInput,
        black.NothingChanged,
        black.ASTSafetyError,
        SyntaxError,
        ValueError,
    ):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
