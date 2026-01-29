#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for IPython library.
Uses atheris for coverage-guided fuzzing.
Focuses on parsing and transformation functions, avoiding code execution.
"""
import sys
import os
import re
import warnings

# Suppress warnings during fuzzing
warnings.filterwarnings("ignore")

import atheris

# Pre-import modules before instrumenting to speed up startup
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input
from IPython.utils.wildcard import filter_ns
from IPython.utils.text import DollarFormatter


@atheris.instrument_func
def TestOneInput(data: bytes):
    """Fuzz target for IPython library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz TransformerManager.transform_cell()
            cell_content = fdp.ConsumeUnicodeNoSurrogates(512)
            tm = TransformerManager()
            tm.transform_cell(cell_content)

        elif choice == 1:
            # Fuzz split_user_input()
            input_line = fdp.ConsumeUnicodeNoSurrogates(128)
            split_user_input(input_line)

        elif choice == 2:
            # Fuzz filter_ns() for wildcard pattern matching
            pattern = fdp.ConsumeUnicodeNoSurrogates(32)
            namespace = {"foo": 1, "bar": 2, "baz": 3}
            filter_ns(namespace, pattern)

        elif choice == 3:
            # Fuzz DollarFormatter
            fmt_string = fdp.ConsumeUnicodeNoSurrogates(64)
            formatter = DollarFormatter()
            formatter.format(fmt_string, test="value", x=1, y=2)

    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
