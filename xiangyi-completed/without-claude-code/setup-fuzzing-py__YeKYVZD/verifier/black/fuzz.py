#!/usr/bin/env python3
"""
Fuzzing driver for Black library using Atheris (LibFuzzer for Python)
Targets: Python code formatting, parsing, and AST operations
"""

import sys
import atheris

# Suppress warnings for cleaner fuzzing output
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import InvalidInput, ASTSafetyError


def TestOneInput(data):
    """Fuzz target for Black library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz format_str with random Python code
            source_code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            mode = Mode()
            black.format_str(source_code, mode=mode)

        elif choice == 1:
            # Fuzz format_str with various mode options
            source_code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            line_length = fdp.ConsumeIntInRange(1, 200)
            is_pyi = fdp.ConsumeBool()

            mode = Mode(
                line_length=line_length,
                is_pyi=is_pyi,
                string_normalization=fdp.ConsumeBool(),
                magic_trailing_comma=fdp.ConsumeBool(),
            )
            black.format_str(source_code, mode=mode)

        elif choice == 2:
            # Fuzz lib2to3_parse directly
            source_code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1500))
            target_versions = set()
            if fdp.ConsumeBool():
                target_versions.add(TargetVersion.PY311)
            black.lib2to3_parse(source_code, target_versions=target_versions)

        elif choice == 3:
            # Fuzz decode_bytes
            byte_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))
            mode = Mode()
            black.decode_bytes(byte_data, mode)

    except (InvalidInput, ASTSafetyError, ValueError, TypeError):
        # Expected exceptions - parsing errors are normal
        pass
    except (SyntaxError, IndentationError, TokenError):
        # Expected Python syntax errors
        pass
    except (UnicodeDecodeError, UnicodeError, LookupError):
        # Expected encoding errors
        pass
    except black.report.NothingChanged:
        # Expected when source doesn't need formatting
        pass
    except AttributeError:
        # Can occur with malformed AST
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        error_type = type(e).__name__
        # Allow some known safe exceptions
        if error_type not in ['RecursionError', 'MemoryError', 'KeyboardInterrupt']:
            # Check if it's a known Black exception
            if not error_type.startswith('Black') and error_type not in ['AssertionError']:
                raise


# Import TokenError for exception handling
try:
    from tokenize import TokenError
except ImportError:
    TokenError = SyntaxError


def main():
    """Main fuzzing entry point."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
