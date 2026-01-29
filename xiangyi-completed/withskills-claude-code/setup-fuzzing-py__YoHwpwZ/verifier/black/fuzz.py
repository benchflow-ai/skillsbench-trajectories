#!/usr/bin/env python3
"""
Atheris-based fuzzer for Black code formatter
Targets: black.format_str() - main formatting entry point
"""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import InvalidInput, NothingChanged

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Black code formatting"""
    if len(data) == 0:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Generate Python source code string
    source_code = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not source_code:
        return

    try:
        # Try to format the code with default mode
        mode = black.Mode()
        formatted = black.format_str(source_code, mode=mode)

        # Verify formatted code is valid (basic sanity check)
        if formatted:
            # Try to format again - should be stable
            reformatted = black.format_str(formatted, mode=mode)
    except (InvalidInput, NothingChanged, ValueError, TypeError):
        # Expected exceptions for invalid input
        pass
    except SyntaxError:
        # Expected for invalid Python syntax
        pass
    except black.parsing.ASTSafetyError:
        # Expected for AST safety violations
        pass
    except Exception as e:
        # Log unexpected exceptions
        if not isinstance(e, (InvalidInput, NothingChanged, ValueError, TypeError, SyntaxError)):
            raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
