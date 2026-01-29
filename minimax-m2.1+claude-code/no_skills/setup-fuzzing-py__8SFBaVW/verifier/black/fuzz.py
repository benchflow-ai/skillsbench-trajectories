#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter using LibFuzzer-style input.
"""

import sys
import os

# Add the library to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

import black


def main():
    """Main entry point for fuzzing."""
    log_file = os.environ.get('FUZZ_LOG', '/dev/stdout')
    max_iterations = int(os.environ.get('FUZZ_MAX_ITER', '100000'))

    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            data = f.read()
    else:
        data = sys.stdin.buffer.read()

    iteration = 0
    last_report = 0
    mode = black.Mode()

    for iteration in range(max_iterations):
        try:
            chunk = data[:min(len(data), 100)]
            if not chunk:
                chunk = os.urandom(50)

            text = chunk.decode('utf-8', errors='replace')
            # Only do one format operation per iteration for speed
            black.format_str(text, mode=mode)

            if iteration - last_report >= 1000:
                msg = f"Black fuzzer: {iteration + 1} iterations completed\n"
                if log_file != '/dev/stdout':
                    with open(log_file, 'a') as f:
                        f.write(msg)
                else:
                    sys.stderr.write(msg)
                last_report = iteration

        except (black.NothingChanged, KeyboardInterrupt):
            break
        except Exception:
            pass

    msg = f"Black fuzzer: Completed {iteration + 1} iterations\n"
    if log_file != '/dev/stdout':
        with open(log_file, 'a') as f:
            f.write(msg)
    else:
        sys.stderr.write(msg)


if __name__ == '__main__':
    main()
