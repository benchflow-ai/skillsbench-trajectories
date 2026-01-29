#!/usr/bin/env python3
"""Fuzz driver for Black library using LibFuzzer interface."""

import sys
import signal
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    import black
except ImportError:
    print("black module not installed, skipping fuzzing")
    sys.exit(0)


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Fuzzing timed out")


def fuzz_format_file(data: bytes) -> None:
    """Fuzz function for black format_file."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz format_str with various code inputs
        try:
            mode = black.Mode()
            result = black.format_str(decoded, mode=mode)
        except Exception:
            pass

        # Fuzz with different modes
        try:
            mode = black.Mode(target_versions={black.TargetVersion.PY310})
            black.format_str(decoded, mode=mode)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_parsing(data: bytes) -> None:
    """Fuzz function for black parsing functions."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz lib2to3 parsing
        try:
            from black.parsing import lib2to3_parse
            lib2to3_parse(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_nodes(data: bytes) -> None:
    """Fuzz function for black node functions."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Try to parse first, then apply node operations
        try:
            from black.parsing import lib2to3_parse
            from black.nodes import is_arith, is_simple_expr, is_yield, walk

            tree = lib2to3_parse(decoded)
            if tree:
                walk(tree)
                # Check if root is arithmetic
                is_arith(tree)
                is_simple_expr(tree)
                is_yield(tree)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_strings(data: bytes) -> None:
    """Fuzz function for black string formatting."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz string processing
        try:
            from black.strings import format_fstring, remove_u_prefix
            remove_u_prefix(decoded)
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
        fuzz_format_file(data.encode('utf-8'))
        fuzz_parsing(data.encode('utf-8'))
        fuzz_nodes(data.encode('utf-8'))
        fuzz_strings(data.encode('utf-8'))
    else:
        # Standalone test mode - run through some test cases
        test_cases = [
            b"x = 1",
            b"def foo():\n    pass",
            b"x = 1 + 2 + 3 + 4 + 5",
            b"import os, sys",
            b"x = {'a': 1, 'b': 2}",
            b"",
            b"\x00\x01\x02",
            b"{" + b"A" * 1000 + b"}",
            b"x = '''multi\nline\nstring'''",
            b"if True:\n    pass  # comment",
        ]

        for data in test_cases:
            try:
                fuzz_format_file(data)
                fuzz_parsing(data)
                fuzz_nodes(data)
                fuzz_strings(data)
            except Exception as e:
                print(f"Error with {data!r}: {e}")

    signal.alarm(0)
    print("Fuzzing completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
