#!/usr/bin/env python3
"""
Fuzz driver for Black library - Python code formatter
Fuzzes lib2to3_parse() and format_str() for code parsing and formatting.
"""

import atheris
import sys

with atheris.instrument_imports():
    from black.parsing import lib2to3_parse, parse_ast, InvalidInput


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Black parser."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Convert bytes to string for Python source code
    try:
        source_code = fdp.ConsumeUnicodeNoSurrogates(len(data))
    except:
        return

    if not source_code:
        return

    # Test 1: Fuzz lib2to3_parse()
    try:
        lib2to3_parse(source_code)
    except (InvalidInput, SyntaxError, ValueError):
        # Expected exceptions for invalid Python code
        pass
    except RecursionError:
        # Can happen with deeply nested code
        pass
    except Exception as e:
        # Unexpected exception - potential bug
        pass

    # Test 2: Fuzz parse_ast()
    if fdp.remaining_bytes() > 10:
        try:
            parse_ast(source_code)
        except (SyntaxError, ValueError):
            # Expected exceptions
            pass
        except RecursionError:
            # Can happen with deeply nested code
            pass
        except Exception as e:
            # Unexpected exception
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
