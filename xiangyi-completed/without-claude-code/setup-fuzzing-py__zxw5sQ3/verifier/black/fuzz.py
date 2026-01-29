#!/usr/bin/env python3
"""
Atheris-based fuzzer for Black library
Targets: Python code parsing and formatting functions
"""

import sys
import atheris

# Suppress output for cleaner fuzzing
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import lib2to3_parse, parse_ast, InvalidInput, ASTSafetyError
    from black.strings import normalize_string_quotes, normalize_unicode_escape_sequences


def TestOneInput(data):
    """Fuzz entry point called by Atheris"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz format_str() - main formatting function
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            mode = Mode(
                line_length=fdp.ConsumeIntInRange(1, 200),
                string_normalization=fdp.ConsumeBool(),
                is_pyi=fdp.ConsumeBool(),
            )
            black.format_str(code, mode=mode)

        elif choice == 1:
            # Fuzz lib2to3_parse()
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            target_versions = set()
            if fdp.ConsumeBool():
                target_versions.add(TargetVersion.PY38)
            lib2to3_parse(code, target_versions=target_versions)

        elif choice == 2:
            # Fuzz parse_ast()
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            parse_ast(code)

        elif choice == 3:
            # Fuzz string normalization functions
            string_literal = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            # Add quotes to make it a valid string literal
            quoted = f'"{string_literal}"'
            normalize_string_quotes(quoted)

        elif choice == 4:
            # Fuzz format_str with different modes
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 300))
            mode = Mode(
                target_versions={TargetVersion.PY38, TargetVersion.PY39},
                line_length=fdp.ConsumeIntInRange(20, 200),
                string_normalization=fdp.ConsumeBool(),
                magic_trailing_comma=fdp.ConsumeBool(),
                is_pyi=fdp.ConsumeBool(),
                is_ipynb=fdp.ConsumeBool(),
            )
            black.format_str(code, mode=mode)

    except (InvalidInput, ASTSafetyError, SyntaxError, ValueError, TypeError,
            IndentationError, TokenError, UnicodeDecodeError, RecursionError):
        # Expected exceptions during fuzzing
        pass
    except black.report.NothingChanged:
        # This is expected when code doesn't need formatting
        pass
    except Exception as e:
        # Catch unexpected exceptions
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["maximum recursion", "memory", "timeout"]):
            pass
        else:
            # Re-raise to find bugs
            raise


def main():
    """Initialize and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    # Import TokenError separately to avoid import issues
    try:
        from tokenize import TokenError
    except ImportError:
        TokenError = SyntaxError
    main()
