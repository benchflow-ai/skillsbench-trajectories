#!/usr/bin/env python3
"""
Fuzz driver for Black library
Tests Python code formatting functions
"""

import sys
import atheris
from atheris import FuzzedDataProvider

# Instrument the black library
with atheris.instrument_imports():
    import black


@atheris.instrument_func
def test_format_str(data):
    """Fuzz black.format_str() with various Python code"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random Python-like code
        code_length = fdp.ConsumeIntInRange(0, 500)
        code = fdp.ConsumeUnicode(code_length)

        if not code:
            return

        # Test with default mode
        try:
            result = black.format_str(code, mode=black.Mode())
        except Exception:
            pass

        # Test with various mode configurations
        modes = [
            black.Mode(line_length=fdp.ConsumeIntInRange(1, 200)),
            black.Mode(
                target_versions=set(),
                line_length=fdp.ConsumeIntInRange(10, 200),
                string_normalization=fdp.ConsumeBool(),
            ),
            black.Mode(
                is_pyi=fdp.ConsumeBool(),
                is_ipynb=fdp.ConsumeBool(),
            ),
        ]

        for mode in modes:
            try:
                result = black.format_str(code, mode=mode)
            except Exception:
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_format_file_contents(data):
    """Fuzz black.format_file_contents()"""
    fdp = FuzzedDataProvider(data)

    try:
        code_length = fdp.ConsumeIntInRange(0, 500)
        code = fdp.ConsumeUnicode(code_length)

        if not code:
            return

        modes = [
            black.Mode(),
            black.Mode(fast=fdp.ConsumeBool()),
            black.Mode(line_length=fdp.ConsumeIntInRange(10, 200)),
        ]

        for mode in modes:
            try:
                result = black.format_file_contents(
                    code,
                    fast=mode.fast,
                    mode=mode,
                )
            except Exception:
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_decode_bytes(data):
    """Fuzz black.decode_bytes() for encoding detection"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random bytes
        byte_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 200))

        modes = [
            black.Mode(),
            black.Mode(),
        ]

        for mode in modes:
            try:
                result = black.decode_bytes(byte_data, mode)
            except Exception:
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_get_features_used(data):
    """Fuzz black.get_features_used() for feature detection"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random Python code
        code_length = fdp.ConsumeIntInRange(0, 500)
        code = fdp.ConsumeUnicode(code_length)

        if not code:
            return

        try:
            import black.ast
            node = black.lib2to3_parse(code)
            features = black.get_features_used(node)
        except Exception:
            pass

    except Exception:
        pass


def TestOneInput(data):
    """Main fuzzing entry point"""
    # Run all test functions
    test_format_str(data)
    test_format_file_contents(data)
    test_decode_bytes(data)
    test_get_features_used(data)


def main():
    """Set up and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
