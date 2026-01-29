#!/usr/bin/env python3
"""Fuzz driver for Black - Python code formatter."""

import atheris
import sys

with atheris.instrument_imports():
    from black import format_str, Mode, TargetVersion
    from black.parsing import lib2to3_parse

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Black code formatter."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test lib2to3_parse() - Core Python parser
    try:
        code = fdp.ConsumeUnicode(len(data))
        target_versions = set()
        if fdp.ConsumeBool():
            target_versions.add(TargetVersion.PY36)
        if fdp.ConsumeBool():
            target_versions.add(TargetVersion.PY37)
        if fdp.ConsumeBool():
            target_versions.add(TargetVersion.PY38)
        if fdp.ConsumeBool():
            target_versions.add(TargetVersion.PY39)
        if fdp.ConsumeBool():
            target_versions.add(TargetVersion.PY310)

        lib2to3_parse(code, target_versions=target_versions)
    except Exception:
        # Expected for invalid Python syntax
        pass

    # Test format_str() - Main formatter entry point
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))

        # Vary Mode parameters
        mode = Mode(
            target_versions=set(),
            line_length=fdp.ConsumeIntInRange(20, 200),
            string_normalization=fdp.ConsumeBool(),
            is_pyi=fdp.ConsumeBool(),
            experimental_string_processing=fdp.ConsumeBool(),
        )

        formatted = format_str(code, mode=mode)

        # Test idempotence: formatting twice should give same result
        formatted_twice = format_str(formatted, mode=mode)
        assert formatted == formatted_twice, "Format is not idempotent"

    except (ValueError, SyntaxError):
        # Expected for invalid code
        pass
    except AssertionError:
        # Idempotence failure
        raise
    except Exception:
        pass

    # Test with various line length limits
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        line_length = fdp.ConsumeIntInRange(10, 200)
        mode = Mode(line_length=line_length)
        format_str(code, mode=mode)
    except Exception:
        pass

    # Test with magic trailing comma
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        mode = Mode(magic_trailing_comma=fdp.ConsumeBool())
        format_str(code, mode=mode)
    except Exception:
        pass

    # Test string normalization options
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        mode = Mode(string_normalization=fdp.ConsumeBool())
        format_str(code, mode=mode)
    except Exception:
        pass

    # Test type stub (pyi) mode
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        mode = Mode(is_pyi=fdp.ConsumeBool())
        format_str(code, mode=mode)
    except Exception:
        pass

    # Test with different target versions
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        versions = set()
        if fdp.ConsumeBool():
            versions.add(TargetVersion.PY36)
        if fdp.ConsumeBool():
            versions.add(TargetVersion.PY310)
        mode = Mode(target_versions=versions)
        format_str(code, mode=mode)
    except Exception:
        pass

    # Test partial line ranges
    try:
        fdp = atheris.FuzzedDataProvider(data)
        code = fdp.ConsumeUnicode(len(data))
        num_lines = code.count('\n') + 1
        if num_lines > 2:
            start_line = fdp.ConsumeIntInRange(1, num_lines - 1)
            end_line = fdp.ConsumeIntInRange(start_line + 1, num_lines)
            lines = [(start_line, end_line)]
            mode = Mode()
            format_str(code, mode=mode, lines=lines)
    except Exception:
        pass

if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
