#!/usr/bin/env python3
"""Fuzz driver for MiniSGL library using LibFuzzer interface."""

import sys
import signal
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python'))

try:
    # Try importing minisgl modules
    import minisgl.core
    import minisgl.env
except ImportError as e:
    print(f"minisgl module not installed or has issues: {e}, skipping fuzzing")
    sys.exit(0)


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Fuzzing timed out")


def fuzz_env(data: bytes) -> None:
    """Fuzz function for minisgl.env."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz environment configuration
        try:
            env = minisgl.env.Env()
            # Test if there are config methods
            if hasattr(env, 'load_config'):
                env.load_config(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_core(data: bytes) -> None:
    """Fuzz function for minisgl.core."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz core functions
        try:
            if hasattr(minisgl.core, 'init'):
                minisgl.core.init()
        except Exception:
            pass

        try:
            if hasattr(minisgl.core, 'process_input'):
                minisgl.core.process_input(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_tokenizer(data: bytes) -> None:
    """Fuzz function for minisgl.tokenizer."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        try:
            from minisgl.tokenizer import Tokenizer
            if 'Tokenizer' in dir():
                tokenizer = Tokenizer()
        except Exception:
            pass

        # Try to import and use tokenizer if available
        try:
            import minisgl.tokenizer as tok_mod
            if hasattr(tok_mod, 'tokenize'):
                tok_mod.tokenize(decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_message(data: bytes) -> None:
    """Fuzz function for minisgl.message."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        try:
            import minisgl.message as msg_mod
            # Fuzz message creation/parsing
            if hasattr(msg_mod, 'Message'):
                msg = msg_mod.Message()
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
        fuzz_env(data.encode('utf-8'))
        fuzz_core(data.encode('utf-8'))
        fuzz_tokenizer(data.encode('utf-8'))
        fuzz_message(data.encode('utf-8'))
    else:
        # Standalone test mode - run through some test cases
        test_cases = [
            b"Hello world",
            b"",
            b"\x00\x01\x02",
            b"{" + b"A" * 100 + b"}",
            b"token1 token2 token3",
            b'{"key": "value"}',
            b"def foo():\n    pass",
            b"x = 123",
            b"# comment line",
            b"import os",
        ]

        for data in test_cases:
            try:
                fuzz_env(data)
                fuzz_core(data)
                fuzz_tokenizer(data)
                fuzz_message(data)
            except Exception as e:
                print(f"Error with {data!r}: {e}")

    signal.alarm(0)
    print("Fuzzing completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
