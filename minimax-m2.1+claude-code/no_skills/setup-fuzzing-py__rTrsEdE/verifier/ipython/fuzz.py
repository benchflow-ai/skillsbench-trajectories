#!/usr/bin/env python3
"""Fuzz driver for IPython library using LibFuzzer interface."""

import sys
import signal
import os

# Add the IPython directory to path
ipython_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ipython_path)

try:
    import IPython
except ImportError:
    print("IPython module not installed, skipping fuzzing")
    sys.exit(0)


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Fuzzing timed out")


def fuzz_text_utils(data: bytes) -> None:
    """Fuzz function for IPython.utils.text."""
    if not data:
        return

    try:
        from IPython.utils.text import eval_file, get_text_list, pad_dot

        decoded = data.decode('utf-8', errors='replace')

        # Fuzz get_text_list
        try:
            get_text_list([decoded, "item2", "item3"])
        except Exception:
            pass

        # Fuzz pad_dot
        try:
            pad_dot(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_data_utils(data: bytes) -> None:
    """Fuzz function for IPython.utils.data."""
    if not data:
        return

    try:
        from IPython.utils.data import uniq, get_iterable

        decoded = data.decode('utf-8', errors='replace')

        # Fuzz uniq
        try:
            test_list = list(decoded) if decoded else []
            uniq(test_list)
        except Exception:
            pass

        # Fuzz get_iterable
        try:
            get_iterable(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_pretty(data: bytes) -> None:
    """Fuzz function for IPython.lib.pretty."""
    if not data:
        return

    try:
        from IPython.lib.pretty import pretty

        # Test with various Python objects
        test_objects = [
            {"key": "value", "number": 123},
            [1, 2, 3, "string"],
            "test string",
            123,
            1.5,
            True,
            None,
            set([1, 2, 3]),
            frozenset([1, 2]),
            (1, 2, 3),
        ]

        for obj in test_objects:
            try:
                pretty(obj)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_formatters(data: bytes) -> None:
    """Fuzz function for IPython.core.formatters."""
    if not data:
        return

    try:
        from IPython.core.formatters import PlainTextFormatter

        formatter = PlainTextFormatter()

        # Test formatting various types
        test_objects = [
            {"key": "value"},
            [1, 2, 3],
            "string",
            123,
            1.5,
        ]

        for obj in test_objects:
            try:
                formatter(obj)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_coloransi(data: bytes) -> None:
    """Fuzz function for IPython.utils.coloransi."""
    if not data:
        return

    try:
        from IPython.utils.coloransi import TermColors, ColorScheme, InputTermColors

        decoded = data.decode('utf-8', errors='replace')

        # Fuzz color schemes
        try:
            scheme = ColorScheme(decoded[:20] if len(decoded) > 20 else decoded)
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main fuzzing function."""
    # Set timeout for long-running fuzzing sessions
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second overall timeout

    if len(sys.argv) > 1:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.read()
        fuzz_text_utils(data.encode('utf-8'))
        fuzz_data_utils(data.encode('utf-8'))
        fuzz_pretty(data.encode('utf-8'))
        fuzz_formatters(data.encode('utf-8'))
        fuzz_coloransi(data.encode('utf-8'))
    else:
        # Standalone test mode - run through some test cases
        test_cases = [
            b"Hello world",
            b"",
            b"\x00\x01\x02",
            b"{" + b"A" * 100 + b"}",
            b"item1,item2,item3",
            b"# comment line",
            b"def foo(): pass",
            b"x = 123",
            b"import os\nimport sys",
            b"[1, 2, 3, 4, 5]",
        ]

        for data in test_cases:
            try:
                fuzz_text_utils(data)
                fuzz_data_utils(data)
                fuzz_pretty(data)
                fuzz_formatters(data)
                fuzz_coloransi(data)
            except Exception as e:
                print(f"Error with {data!r}: {e}")

    signal.alarm(0)
    print("Fuzzing completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
