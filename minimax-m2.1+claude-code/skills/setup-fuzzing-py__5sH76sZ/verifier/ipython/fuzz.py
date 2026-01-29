#!/usr/bin/env python3
"""
Fuzz driver for IPython library
Tests text processing and utility functions
"""

import sys
import atheris
from atheris import FuzzedDataProvider

# Instrument the IPython library
with atheris.instrument_imports():
    from IPython.utils import text


@atheris.instrument_func
def test_columnize(data):
    """Fuzz IPython.utils.text.columnize()"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate list of strings
        num_strings = fdp.ConsumeIntInRange(0, 50)
        string_list = []
        for _ in range(num_strings):
            string_list.append(fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 20)))

        if not string_list:
            return

        # Test with various configurations
        displaywidth = fdp.ConsumeIntInRange(10, 200)
        separator = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 5))

        try:
            result = text.columnize(string_list, displaywidth=displaywidth)
        except Exception:
            pass

        try:
            result = text.columnize(string_list, separator=separator)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_sre_match(data):
    """Fuzz IPython.utils.text.sre_match()"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate regex pattern and string
        pattern = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50))
        string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

        if not pattern or not string:
            return

        try:
            result = text.sre_match(pattern, string)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_column_data(data):
    """Fuzz IPython.utils.text.ColumnData and related functions"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate column widths and data
        num_cols = fdp.ConsumeIntInRange(1, 10)
        widths = []
        for _ in range(num_cols):
            widths.append(fdp.ConsumeIntInRange(1, 50))

        try:
            cd = text.ColumnData(widths)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_dollar_replacer(data):
    """Fuzz IPython.utils.text.dollar_replacer()"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate template string
        template = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

        if not template:
            return

        # Generate variable dictionary
        var_dict = {}
        num_vars = fdp.ConsumeIntInRange(0, 10)
        for _ in range(num_vars):
            key = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 10))
            value = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 20))
            var_dict[key] = value

        try:
            dr = text.DollarReplacer(var_dict)
            result = dr.replace(template)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_wrap_preserve(data):
    """Fuzz text wrapping functions"""
    fdp = FuzzedDataProvider(data)

    try:
        text_to_wrap = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))
        width = fdp.ConsumeIntInRange(10, 100)

        if not text_to_wrap:
            return

        try:
            result = text.wrap_preserve(text_to_wrap, width=width)
        except Exception:
            pass

        try:
            result = text.wrap_fill(text_to_wrap, width=width)
        except Exception:
            pass

    except Exception:
        pass


def TestOneInput(data):
    """Main fuzzing entry point"""
    # Run all test functions
    test_columnize(data)
    test_sre_match(data)
    test_column_data(data)
    test_dollar_replacer(data)
    test_wrap_preserve(data)


def main():
    """Set up and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
