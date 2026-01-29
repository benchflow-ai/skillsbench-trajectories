#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for IPython input transformers.
Uses Atheris for LibFuzzer-style fuzzing.
"""
import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for IPython input transformation."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import IPython modules inside the function for instrumentation
    from IPython.core.inputtransformer2 import (
        PromptStripper,
        classic_prompt,
        ipython_prompt,
        cell_magic,
        leading_empty_lines,
        leading_indent,
        TransformerManager,
    )

    # Generate input lines from fuzz data
    num_lines = fdp.ConsumeIntInRange(1, 20)
    lines = []
    for _ in range(num_lines):
        line = fdp.ConsumeUnicodeNoSurrogates(256)
        if line:
            # Ensure line ends with newline for proper processing
            if not line.endswith('\n'):
                line = line + '\n'
            lines.append(line)

    if not lines:
        return

    # Test 1: classic_prompt stripper
    try:
        classic_prompt(lines.copy())
    except (ValueError, TypeError, IndexError, AttributeError):
        pass

    # Test 2: ipython_prompt stripper
    try:
        ipython_prompt(lines.copy())
    except (ValueError, TypeError, IndexError, AttributeError):
        pass

    # Test 3: cell_magic transformer
    try:
        cell_magic(lines.copy())
    except (ValueError, TypeError, IndexError, AttributeError, SyntaxError):
        pass

    # Test 4: leading_empty_lines
    try:
        leading_empty_lines(lines.copy())
    except (ValueError, TypeError, IndexError):
        pass

    # Test 5: leading_indent
    try:
        leading_indent(lines.copy())
    except (ValueError, TypeError, IndexError):
        pass

    # Test 6: TransformerManager.transform_cell
    try:
        tm = TransformerManager()
        cell_content = fdp.ConsumeUnicodeNoSurrogates(1024)
        if cell_content:
            tm.transform_cell(cell_content)
    except (ValueError, TypeError, IndexError, SyntaxError,
            tokenize.TokenizeError, AttributeError):
        pass

    # Test 7: Test with magic command prefixes
    magic_lines = ['%%' + fdp.ConsumeUnicodeNoSurrogates(64) + '\n']
    magic_lines.extend(lines[:5])
    try:
        cell_magic(magic_lines)
    except (ValueError, TypeError, IndexError, AttributeError, SyntaxError):
        pass


import tokenize


def main():
    # Instrument IPython modules for coverage
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
