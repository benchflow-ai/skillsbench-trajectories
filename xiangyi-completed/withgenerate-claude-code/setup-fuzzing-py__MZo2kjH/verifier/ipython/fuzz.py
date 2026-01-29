#!/usr/bin/env python3
"""Fuzz driver for IPython library - input transformation."""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core import inputtransformer2


def TestOneInput(data: bytes) -> None:
    """Main fuzz target function for IPython input transformers."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Classic prompt stripping
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        inputtransformer2.classic_prompt(lines)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass

    # Test 2: IPython prompt stripping
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        inputtransformer2.ipython_prompt(lines)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass

    # Test 3: Cell magic processing
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        inputtransformer2.cell_magic(lines)
    except (ValueError, TypeError, SyntaxError, RecursionError, AttributeError):
        pass

    # Test 4: Leading empty lines removal
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        inputtransformer2.leading_empty_lines(lines)
    except (ValueError, TypeError):
        pass

    # Test 5: Leading indent removal
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        inputtransformer2.leading_indent(lines)
    except (ValueError, TypeError):
        pass

    # Test 6: Find end of continued line
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        lines = code.splitlines(keepends=True)
        if lines:
            start_line = fdp.ConsumeIntInRange(0, max(0, len(lines) - 1))
            inputtransformer2.find_end_of_continued_line(lines, start_line)
    except (ValueError, TypeError, IndexError):
        pass

    # Test 7: TransformerManager transform_cell
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 1000)
        )
        tm = inputtransformer2.TransformerManager()
        tm.transform_cell(code)
    except (
        ValueError,
        TypeError,
        SyntaxError,
        RecursionError,
        AttributeError,
        IndentationError,
        TabError,
    ):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
