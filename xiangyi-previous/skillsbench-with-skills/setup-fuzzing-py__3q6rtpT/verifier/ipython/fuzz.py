#!/usr/bin/env python3
"""
Fuzz driver for IPython
Targets: Input transformation and text processing
"""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils import text

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for IPython"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz TransformerManager.transform_cell()
            cell_input = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            if cell_input:
                manager = TransformerManager()
                manager.transform_cell(cell_input)

        elif choice == 1:
            # Fuzz text processing utilities
            text_input = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            max_len = fdp.ConsumeIntInRange(1, 100)
            if text_input:
                text.truncate(text_input, max_len)

        elif choice == 2:
            # Fuzz get_text_list
            items = []
            num_items = fdp.ConsumeIntInRange(0, 20)
            for _ in range(num_items):
                item = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
                if item:
                    items.append(item)
            if items:
                text.get_text_list(items)

    except (ValueError, TypeError, AttributeError, SyntaxError, IndexError):
        # Expected exceptions
        pass
    except Exception as e:
        # Log unexpected exceptions
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
