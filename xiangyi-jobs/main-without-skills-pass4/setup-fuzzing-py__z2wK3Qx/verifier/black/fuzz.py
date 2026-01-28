import sys

import atheris

with atheris.instrument_imports():
    import black


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    source = fdp.ConsumeUnicodeNoSurrogates(800)
    line_length = fdp.ConsumeIntInRange(1, 200)
    mode = black.FileMode(
        line_length=line_length,
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
        preview=fdp.ConsumeBool(),
    )
    try:
        formatted = black.format_str(source, mode=mode)
        if fdp.ConsumeBool():
            black.format_str(formatted, mode=mode)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
