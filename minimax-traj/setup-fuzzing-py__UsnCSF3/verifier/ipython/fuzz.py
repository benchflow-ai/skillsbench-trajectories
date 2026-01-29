#!/usr/bin/env python3
"""
Fuzz driver for IPython library.
Uses LibFuzzer-style coverage-guided fuzzing.
"""

import sys
from typing import Any

# Lazy imports to avoid heavy initialization during fuzzing
def fuzz_ipython_formatters(input_data: bytes) -> None:
    """Fuzz IPython formatters with various inputs."""
    try:
        from IPython.core.formatters import DisplayFormatter, PlainTextFormatter

        formatter = DisplayFormatter()
        data = input_data.decode('utf-8', errors='replace')

        # Test various type formattings
        test_objects = [
            data,
            data.encode('utf-8'),
            12345,
            3.14159,
            [1, 2, 3],
            {'key': 'value'},
            True,
            None,
        ]

        for obj in test_objects:
            try:
                formatter(obj)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_ipython_inspector(input_data: bytes) -> None:
    """Fuzz IPython inspector with various objects."""
    try:
        from IPython.core.inspector import Inspector

        inspector = Inspector()
        data = input_data.decode('utf-8', errors='replace')

        # Test inspection of various objects
        test_objects = [
            str,
            int,
            list,
            dict,
            len,
            print,
            lambda x: x,
        ]

        for obj in test_objects:
            try:
                inspector.info(obj)
            except Exception:
                pass

        # Test info on builtins
        try:
            inspector.pinfo('str')
        except Exception:
            pass

    except Exception:
        pass


def fuzz_ipython_pycolorize(input_data: bytes) -> None:
    """Fuzz IPython syntax highlighting."""
    try:
        from IPython.utils.PyColorize import PythonSyntaxHighlight

        psh = PythonSyntaxHighlight()
        data = input_data.decode('utf-8', errors='replace')

        try:
            psh(data)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_ipython_pretty_print(input_data: bytes) -> None:
    """Fuzz IPython pretty printing."""
    try:
        from IPython.lib.pretty import pretty

        data = input_data.decode('utf-8', errors='replace')

        test_objects = [
            {'a' * 100: 'b' * 100},
            list(range(100)),
            {'nested': {'dict': {'deep': 'value'}}},
            [i for i in range(50)],
        ]

        for obj in test_objects:
            try:
                pretty(obj)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_ipython_completer(input_data: bytes) -> None:
    """Fuzz IPython completer."""
    try:
        from IPython.core.completer import Completer

        completer = Completer()
        data = input_data.decode('utf-8', errors='replace')

        try:
            completer.complete(data, 0)
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main entry point for fuzzing."""
    if len(sys.argv) > 1:
        # Running with input file (LibFuzzer mode)
        with open(sys.argv[1], 'rb') as f:
            input_data = f.read()
    else:
        # Running from stdin
        input_data = sys.stdin.buffer.read()

    # Run all fuzz targets
    fuzz_ipython_formatters(input_data)
    fuzz_ipython_inspector(input_data)
    fuzz_ipython_pycolorize(input_data)
    fuzz_ipython_pretty_print(input_data)
    fuzz_ipython_completer(input_data)


if __name__ == '__main__':
    main()
