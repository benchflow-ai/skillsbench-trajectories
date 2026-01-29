#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for ipython library.
Tests ipython's input parsing, display, and text utilities.
"""

import sys
import atheris
from IPython.core import splitinput
from IPython.utils import text, wildcard


def __test_one_input(data: bytes) -> None:
    """Fuzz driver for ipython library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Split fuzzed data into parts for different test strategies
    action = fdp.ConsumeIntInRange(0, 6)

    if action == 0:
        # Test split_user_input()
        try:
            input_line = fdp.ConsumeUnicode(512)
            splitinput.split_user_input(input_line)
        except (ValueError, AttributeError, TypeError):
            pass

    elif action == 1:
        # Test text.indent()
        try:
            string = fdp.ConsumeUnicode(1024)
            nspaces = fdp.ConsumeIntInRange(0, 16)
            ntabs = fdp.ConsumeIntInRange(0, 8)
            flatten = fdp.ConsumeBool()
            text.indent(string, nspaces=nspaces, ntabs=ntabs, flatten=flatten)
        except (ValueError, TypeError, AttributeError):
            pass

    elif action == 2:
        # Test text.dedent()
        try:
            string = fdp.ConsumeUnicode(1024)
            text.dedent(string)
        except (ValueError, TypeError, AttributeError):
            pass

    elif action == 3:
        # Test text.marquee()
        try:
            txt = fdp.ConsumeUnicode(256)
            width = fdp.ConsumeIntInRange(10, 120)
            mark = fdp.ConsumeUnicode(4)
            text.marquee(txt, width=width, mark=mark)
        except (ValueError, TypeError, AttributeError):
            pass

    elif action == 4:
        # Test text.format_screen()
        try:
            strng = fdp.ConsumeUnicode(2048)
            text.format_screen(strng)
        except (ValueError, TypeError, AttributeError):
            pass

    elif action == 5:
        # Test text.strip_email_quotes()
        try:
            text_str = fdp.ConsumeUnicode(1024)
            text.strip_email_quotes(text_str)
        except (ValueError, TypeError, AttributeError):
            pass

    elif action == 6:
        # Test wildcard.filter_ns()
        try:
            # Create a simple namespace dict
            ns = {}
            for _ in range(fdp.ConsumeIntInRange(0, 20)):
                key = fdp.ConsumeUnicode(32)
                choice = fdp.ConsumeIntInRange(0, 3)
                if choice == 0:
                    ns[key] = fdp.ConsumeInt(1000)
                elif choice == 1:
                    ns[key] = fdp.ConsumeUnicode(100)
                else:
                    ns[key] = fdp.ConsumeBool()

            name_pattern = fdp.ConsumeUnicode(32)
            ignore_case = fdp.ConsumeBool()

            wildcard.filter_ns(ns, name_pattern, ignore_case=ignore_case)
        except (ValueError, TypeError, AttributeError, KeyError, Exception):
            pass


# Initialize atheris for code coverage guidance
atheris.Setup(sys.argv, __test_one_input)

if __name__ == "__main__":
    atheris.Fuzz()
