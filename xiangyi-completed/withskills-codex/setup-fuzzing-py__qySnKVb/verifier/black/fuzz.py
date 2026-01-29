import sys

import atheris

with atheris.instrument_imports():
    import black


def _make_mode(fdp: atheris.FuzzedDataProvider) -> black.Mode:
    line_length = fdp.ConsumeIntInRange(20, 200)
    string_normalization = fdp.ConsumeBool()
    magic_trailing_comma = fdp.ConsumeBool()
    is_pyi = fdp.ConsumeBool()
    return black.Mode(
        line_length=line_length,
        string_normalization=string_normalization,
        magic_trailing_comma=magic_trailing_comma,
        is_pyi=is_pyi,
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)
    mode = _make_mode(fdp)

    try:
        _ = black.format_str(text, mode=mode)
    except black.InvalidInput:
        return
    except Exception:
        raise

    try:
        _ = black.parsing.lib2to3_parse(text, target_versions=mode.target_versions)
    except black.InvalidInput:
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
