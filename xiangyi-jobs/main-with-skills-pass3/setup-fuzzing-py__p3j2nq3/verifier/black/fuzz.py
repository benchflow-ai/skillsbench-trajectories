import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import parsing


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(500)

    mode = black.Mode(
        line_length=fdp.ConsumeIntInRange(1, 200),
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
        preview=fdp.ConsumeBool(),
        unstable=fdp.ConsumeBool(),
    )

    _safe_call(black.format_str, src, mode=mode)
    _safe_call(parsing.parse_ast, src)
    _safe_call(parsing.lib2to3_parse, src, mode.target_versions)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
