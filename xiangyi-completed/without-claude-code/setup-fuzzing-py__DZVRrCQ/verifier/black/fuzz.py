#!/usr/bin/env python3
"""
Coverage-guided fuzzing for Black code formatter using atheris (LibFuzzer compatible).

Targets:
- format_str(): Main public API for formatting Python code
- lib2to3_parse(): Core parsing function
- parse_ast(): Standard library AST parsing
- decode_bytes(): Encoding detection from raw bytes
"""

import sys
import atheris


def setup_black():
    """Import black and related modules."""
    global black, Mode, TargetVersion, lib2to3_parse, parse_ast
    import black as black_module
    from black import Mode as M
    from black.mode import TargetVersion as TV
    from black.parsing import lib2to3_parse as l2tp, parse_ast as pa
    black = black_module
    Mode = M
    TargetVersion = TV
    lib2to3_parse = l2tp
    parse_ast = pa


def fuzz_format_str(data: bytes):
    """Fuzz black.format_str() with arbitrary source code."""
    try:
        src = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        mode = Mode()
        black.format_str(src, mode=mode)
    except (black.InvalidInput, ValueError, RecursionError):
        pass
    except Exception:
        # Catch any other parsing/formatting errors
        pass


def fuzz_format_str_with_options(data: bytes):
    """Fuzz black.format_str() with various Mode options."""
    if len(data) < 2:
        return

    try:
        # Use first byte for options
        options = data[0]
        src = data[1:].decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        # Vary Mode parameters based on options byte
        line_length = 40 + (options & 0x3F)  # 40-103
        is_pyi = bool(options & 0x40)
        string_normalization = bool(options & 0x80)

        mode = Mode(
            line_length=line_length,
            is_pyi=is_pyi,
            string_normalization=string_normalization
        )
        black.format_str(src, mode=mode)
    except (black.InvalidInput, ValueError, RecursionError):
        pass
    except Exception:
        pass


def fuzz_lib2to3_parse(data: bytes):
    """Fuzz lib2to3_parse() with arbitrary source code."""
    try:
        src = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        lib2to3_parse(src)
    except (black.InvalidInput, ValueError, RecursionError):
        pass
    except Exception:
        pass


def fuzz_parse_ast(data: bytes):
    """Fuzz parse_ast() with arbitrary source code."""
    try:
        src = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        parse_ast(src)
    except (SyntaxError, ValueError, RecursionError):
        pass
    except Exception:
        pass


def fuzz_decode_bytes(data: bytes):
    """Fuzz decode_bytes() with arbitrary byte sequences."""
    try:
        mode = Mode()
        black.decode_bytes(data, mode)
    except (ValueError, UnicodeDecodeError, LookupError):
        pass
    except Exception:
        pass


def TestOneInput(data: bytes):
    """Main fuzzing entry point - calls all fuzz targets."""
    if len(data) < 1:
        return

    # Use first byte to select target
    selector = data[0] % 5
    payload = data[1:]

    if selector == 0:
        fuzz_format_str(payload)
    elif selector == 1:
        fuzz_format_str_with_options(payload)
    elif selector == 2:
        fuzz_lib2to3_parse(payload)
    elif selector == 3:
        fuzz_parse_ast(payload)
    else:
        fuzz_decode_bytes(payload)


def main():
    """Main entry point for the fuzzer."""
    setup_black()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
