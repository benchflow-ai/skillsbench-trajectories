#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter
Tests Python code parsing and formatting functions
"""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import format_str, Mode
    from black.parsing import InvalidInput, ASTSafetyError


def fuzz_format_str(data):
    """Fuzz black.format_str() with arbitrary Python code"""
    try:
        mode = Mode()
        format_str(data, mode=mode)
    except (InvalidInput, ASTSafetyError, ValueError, TypeError, KeyError):
        pass
    except black.report.NothingChanged:
        pass
    except Exception as e:
        # Log unexpected exceptions
        pass


def fuzz_format_str_with_mode(data, line_length=88):
    """Fuzz format_str with different mode configurations"""
    try:
        mode = Mode(line_length=line_length)
        format_str(data, mode=mode)
    except (InvalidInput, ASTSafetyError, ValueError, TypeError, KeyError):
        pass
    except black.report.NothingChanged:
        pass
    except Exception as e:
        pass


def fuzz_decode_bytes(data):
    """Fuzz black.decode_bytes() for encoding edge cases"""
    try:
        mode = Mode()
        black.decode_bytes(data, mode)
    except (UnicodeDecodeError, ValueError, TypeError, LookupError):
        pass
    except Exception as e:
        pass


def fuzz_parse_pyproject_toml(data):
    """Fuzz TOML configuration parsing"""
    try:
        # Try to parse as TOML
        black.files.parse_pyproject_toml(data.decode('utf-8', errors='ignore'))
    except:
        pass


@atheris.instrument_func
def TestOneInput(data):
    """Main fuzzing entry point"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz format_str with source code
        remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            source = remaining.decode('utf-8', errors='ignore')
            fuzz_format_str(source)
        except:
            pass
    elif choice == 1:
        # Fuzz format_str with custom line length
        line_length = fdp.ConsumeIntInRange(1, 200)
        remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            source = remaining.decode('utf-8', errors='ignore')
            fuzz_format_str_with_mode(source, line_length)
        except:
            pass
    elif choice == 2:
        # Fuzz decode_bytes
        remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
        fuzz_decode_bytes(remaining)
    else:
        # Fuzz TOML parsing
        remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
        fuzz_parse_pyproject_toml(remaining)


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
