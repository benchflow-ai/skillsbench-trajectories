#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter
Focuses on format_str(), lib2to3_parse(), and normalize_string_quotes()
"""

import atheris
import sys

with atheris.instrument_imports():
    import black
    from black import format_str, Mode, TargetVersion
    from black.strings import normalize_string_quotes
    from black.parsing import lib2to3_parse


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Black library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)
    strategy = fdp.ConsumeIntInRange(0, 3)

    if strategy == 0:
        # Fuzz format_str() - main formatting entry point
        try:
            source_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 2048))
            mode = Mode(
                target_versions={TargetVersion.PY310},
                line_length=fdp.ConsumeIntInRange(10, 200),
                is_pyi=fdp.ConsumeBool(),
            )
            black.format_str(source_code, mode=mode)
        except (SyntaxError, ValueError, black.NothingChanged,
                black.InvalidInput, black.EmptyNodeError):
            pass
        except Exception:
            pass

    elif strategy == 1:
        # Fuzz lib2to3_parse() - parser entry point
        try:
            source_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 1024))
            target_versions = set()
            if fdp.ConsumeBool():
                target_versions.add(TargetVersion.PY310)
            else:
                target_versions.add(TargetVersion.PY39)
            lib2to3_parse(source_code, target_versions=target_versions)
        except (SyntaxError, ValueError):
            pass

    elif strategy == 2:
        # Fuzz string normalization
        try:
            # Create a valid string literal
            string_content = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 256))
            quote_char = fdp.PickValueInList(['"', "'"])
            string_literal = f'{quote_char}{string_content}{quote_char}'
            normalize_string_quotes(string_literal)
        except (ValueError, TypeError, AssertionError):
            pass

    elif strategy == 3:
        # Fuzz with complex Python code patterns
        try:
            patterns = [
                "def f(): pass",
                "class C: pass",
                "x = [1, 2, 3]",
                "d = {'a': 1}",
                "f'{x}'",
                "lambda x: x",
                "try: pass\nexcept: pass",
            ]
            base_code = fdp.PickValueInList(patterns)
            mutation = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 256))
            source_code = base_code + "\n" + mutation

            mode = Mode(line_length=88, is_pyi=False)
            black.format_str(source_code, mode=mode)
        except (SyntaxError, ValueError, black.NothingChanged,
                black.InvalidInput, black.EmptyNodeError):
            pass
        except Exception:
            pass


if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
