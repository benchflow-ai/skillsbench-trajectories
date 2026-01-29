import sys

import atheris

with atheris.instrument_imports():
    import black


EXPECTED = (
    black.InvalidInput,
    SyntaxError,
    ValueError,
    TypeError,
    OverflowError,
)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    code = fdp.ConsumeUnicodeNoSurrogates(4096)
    line_length = fdp.ConsumeIntInRange(1, 200)
    string_normalization = fdp.ConsumeBool()
    magic_trailing_comma = fdp.ConsumeBool()
    mode = black.FileMode(
        line_length=line_length,
        string_normalization=string_normalization,
        magic_trailing_comma=magic_trailing_comma,
    )
    try:
        black.parsing.parse_ast(code)
        black.format_str(code, mode=mode)
    except EXPECTED:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
