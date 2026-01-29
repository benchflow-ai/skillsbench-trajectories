#!/usr/bin/env python3
"""
Fuzzing driver for black library.
Targets: black.format_str(), parsing functions
"""

import atheris
import sys

# Instrument the library before importing
atheris.instrument_imports(["black"])

import black


@atheris.instrument_func
def fuzz_black_format_str(data):
    """Fuzz black.format_str() - main formatting function"""
    try:
        source = data.decode('utf-8', errors='ignore')

        # Try default formatting
        result = black.format_str(source, mode=black.FileMode())

    except black.NothingChanged:
        # Expected - source already formatted
        return
    except (ValueError, SyntaxError, TypeError):
        # Expected - invalid Python source
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_black_with_mode_variations(data):
    """Fuzz black.format_str() with different mode configurations"""
    try:
        fdp = atheris.FuzzedDataProvider(data)
        source = fdp.ConsumeString(size=500)

        # Vary formatting options
        line_length = fdp.ConsumeIntInRange(10, 200)
        string_normalization = fdp.ConsumeBool()
        is_pyi = fdp.ConsumeBool()
        magic_trailing_comma = fdp.ConsumeBool()

        mode = black.FileMode(
            line_length=line_length,
            string_normalization=string_normalization,
            is_pyi=is_pyi,
            magic_trailing_comma=magic_trailing_comma,
        )

        result = black.format_str(source, mode=mode)

    except black.NothingChanged:
        return
    except (ValueError, SyntaxError, TypeError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_black_lib2to3_parse(data):
    """Fuzz lib2to3 parser directly"""
    try:
        source = data.decode('utf-8', errors='ignore')

        # Try parsing with lib2to3
        from black.parsing import lib2to3_parse

        result = lib2to3_parse(source)

    except SyntaxError:
        # Expected - invalid syntax
        return
    except (ValueError, TypeError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_black_parse_ast(data):
    """Fuzz AST parsing function"""
    try:
        source = data.decode('utf-8', errors='ignore')

        # Try parsing to AST
        from black.parsing import parse_ast

        result = parse_ast(source)

    except SyntaxError:
        # Expected - invalid syntax
        return
    except (ValueError, TypeError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def test_black_fuzzer(data):
    """Main fuzz target dispatcher"""
    if len(data) < 2:
        return

    # Route to different fuzz targets based on first byte
    target = data[0] % 3
    remaining_data = data[1:]

    if target == 0:
        fuzz_black_format_str(remaining_data)
    elif target == 1:
        fuzz_black_with_mode_variations(remaining_data)
    else:
        fuzz_black_lib2to3_parse(remaining_data)


# Setup and run fuzzer
atheris.Setup(sys.argv, test_black_fuzzer)
atheris.Fuzz()
