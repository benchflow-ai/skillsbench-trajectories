import sys

import atheris

with atheris.instrument_imports():
    import black
    from black import numerics as black_numerics
    from black import parsing as black_parsing
    from black import ranges as black_ranges


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    op = fdp.ConsumeIntInRange(0, 3)
    try:
        if op == 0:
            src = fdp.ConsumeUnicodeNoSurrogates(400)
            mode = black.Mode()
            black.format_str(src, mode=mode)
        elif op == 1:
            src = fdp.ConsumeUnicodeNoSurrogates(400)
            try:
                black_parsing.parse_ast(src)
            except Exception:
                pass
            try:
                black_parsing.lib2to3_parse(src)
            except Exception:
                pass
        elif op == 2:
            spec = fdp.ConsumeUnicodeNoSurrogates(50)
            try:
                black_ranges.parse_line_ranges([spec])
            except Exception:
                pass
        else:
            text = fdp.ConsumeUnicodeNoSurrogates(40)
            for func in (
                black_numerics.format_hex,
                black_numerics.format_scientific_notation,
                black_numerics.format_complex_number,
                black_numerics.format_float_or_int_string,
            ):
                try:
                    func(text)
                except Exception:
                    pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
