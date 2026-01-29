#!/usr/bin/env python3
"""Fuzz driver for IPython - Interactive Python shell input processing."""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.splitinput import split_user_input
    from IPython.utils._process_common import arg_split
    from IPython.core.inputtransformer2 import TransformerManager

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for IPython input processing functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test split_user_input() - Core line splitting
    try:
        line = fdp.ConsumeUnicode(len(data))
        split_user_input(line)
    except Exception:
        pass

    # Test arg_split() - Argument tokenization
    try:
        fdp = atheris.FuzzedDataProvider(data)
        arg_string = fdp.ConsumeUnicode(len(data))
        posix = fdp.ConsumeBool()
        strict = fdp.ConsumeBool()
        arg_split(arg_string, posix=posix, strict=strict)
    except Exception:
        pass

    # Test TransformerManager.transform_cell() - Cell transformation
    try:
        fdp = atheris.FuzzedDataProvider(data)
        cell_content = fdp.ConsumeUnicode(len(data))
        manager = TransformerManager()
        manager.transform_cell(cell_content)
    except Exception:
        pass

    # Test check_complete() - Syntax completion checking
    try:
        fdp = atheris.FuzzedDataProvider(data)
        cell_content = fdp.ConsumeUnicode(len(data))
        manager = TransformerManager()
        manager.check_complete(cell_content)
    except Exception:
        pass

    # Test multi-line input handling
    try:
        fdp = atheris.FuzzedDataProvider(data)
        lines = []
        num_lines = fdp.ConsumeIntInRange(1, 20)
        for _ in range(num_lines):
            line = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 200))
            lines.append(line)

        combined = '\n'.join(lines)
        manager = TransformerManager()
        manager.transform_cell(combined)
    except Exception:
        pass

    # Test escape character handling
    try:
        fdp = atheris.FuzzedDataProvider(data)
        escape_char = fdp.PickValueInList(['%', '!', '?', '!!', '??'])
        rest = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 200))
        line = f"{escape_char}{rest}"
        split_user_input(line)
    except Exception:
        pass

    # Test magic-like syntax
    try:
        fdp = atheris.FuzzedDataProvider(data)
        magic_name = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50))
        magic_args = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))
        line = f"%{magic_name} {magic_args}"
        split_user_input(line)
        arg_split(magic_args, strict=False)
    except Exception:
        pass

    # Test continuation lines
    try:
        fdp = atheris.FuzzedDataProvider(data)
        lines = []
        for _ in range(fdp.ConsumeIntInRange(2, 10)):
            line = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
            if fdp.ConsumeBool():
                line += '\\'  # Add continuation
            lines.append(line)

        combined = '\n'.join(lines)
        manager = TransformerManager()
        manager.transform_cell(combined)
    except Exception:
        pass

if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
