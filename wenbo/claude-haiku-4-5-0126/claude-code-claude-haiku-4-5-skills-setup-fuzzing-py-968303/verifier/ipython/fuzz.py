#!/usr/bin/env python3
"""
Fuzz driver for IPython library
Focuses on split_user_input(), transform_cell(), and parse_argstring()
"""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.splitinput import split_user_input
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.magic_arguments import magic_arguments, argument
    import IPython


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for IPython library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)
    strategy = fdp.ConsumeIntInRange(0, 2)

    if strategy == 0:
        # Fuzz split_user_input()
        try:
            user_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 512))
            split_user_input(user_input)
        except (ValueError, TypeError, AttributeError):
            pass

    elif strategy == 1:
        # Fuzz transform_cell()
        try:
            cell_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 1024))
            # Create transformer manager
            transformer = TransformerManager()
            transformer.transform_cell(cell_code)
        except (ValueError, TypeError, SyntaxError, AttributeError):
            pass

    elif strategy == 2:
        # Fuzz with various escape sequences and magic commands
        try:
            escape_chars = fdp.PickValueInList(['!', '%', '?', ';;', '%%'])
            magic_name = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 32))
            args = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 256))
            user_input = f'{escape_chars}{magic_name} {args}'
            split_user_input(user_input)
        except (ValueError, TypeError, AttributeError):
            pass


if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
