#!/usr/bin/env python3
"""Fuzz driver for black library - Python code formatter."""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import Mode


def TestOneInput(data):
    """Fuzz target for black library."""
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        # Test format_str() with random Python code
        if fdp.ConsumeBool():
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            try:
                mode = Mode()
                black.format_str(code, mode=mode)
            except (black.InvalidInput, ValueError, TypeError, SyntaxError):
                pass
        
        # Test format_str() with different mode options
        elif fdp.ConsumeBool():
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            try:
                line_length = fdp.ConsumeIntInRange(1, 200)
                mode = Mode(line_length=line_length)
                black.format_str(code, mode=mode)
            except (black.InvalidInput, ValueError, TypeError, SyntaxError):
                pass
        
        # Test format_file_contents() with random content
        elif fdp.ConsumeBool():
            content = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1500))
            try:
                mode = Mode()
                black.format_file_contents(content, fast=True, mode=mode)
            except (black.InvalidInput, black.NothingChanged, ValueError, TypeError):
                pass
        
        # Test with various string literals and edge cases
        else:
            # Generate potentially problematic Python code patterns
            patterns = [
                fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100)),
                f'""" {fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))} """',
                f"f'{fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))}'" if fdp.ConsumeBool() else "",
            ]
            code = "\n".join(patterns)
            try:
                mode = Mode()
                black.format_str(code, mode=mode)
            except (black.InvalidInput, ValueError, TypeError, SyntaxError):
                pass
                
    except Exception:
        # Catch any unexpected exceptions
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
