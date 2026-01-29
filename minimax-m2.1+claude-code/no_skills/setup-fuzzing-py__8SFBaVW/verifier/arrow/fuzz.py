#!/usr/bin/env python3
"""
Fuzz driver for Arrow library using LibFuzzer-style input.
"""

import sys
import os

# Add the library to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arrow


def fuzz_arrow_get(data: bytes) -> None:
    """Fuzz arrow.get() with various string inputs."""
    try:
        text = data.decode('utf-8', errors='replace')
        arrow.get(text)
    except Exception:
        pass


def fuzz_arrow_factory(data: bytes) -> None:
    """Fuzz ArrowFactory methods."""
    try:
        text = data.decode('utf-8', errors='replace')
        arrow.get(text)
        dt = arrow.get('2020-01-01')
        dt.shift(days=1)
        dt.shift(hours=1)
        dt.shift(minutes=1)
        dt.shift(seconds=1)
    except Exception:
        pass


def fuzz_arrow_format(data: bytes) -> None:
    """Fuzz Arrow formatting functions."""
    try:
        text = data.decode('utf-8', errors='replace')
        dt = arrow.get(text)
        dt.format('YYYY-MM-DD')
        dt.format('HH:mm:ss')
        dt.format('MMMM DD, YYYY')
        dt.format('YYYY-MM-DD HH:mm:ssZZ')
    except Exception:
        pass


def fuzz_arrow_properties(data: bytes) -> None:
    """Fuzz Arrow object properties."""
    try:
        text = data.decode('utf-8', errors='replace')
        dt = arrow.get(text)
        _ = dt.year
        _ = dt.month
        _ = dt.day
        _ = dt.hour
        _ = dt.minute
        _ = dt.second
        _ = dt.microsecond
        _ = dt.timestamp
        _ = dt.datetime
        _ = dt.naive
        _ = dt.tzinfo
    except Exception:
        pass


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
    for iteration in range(max_iterations):
        try:
            chunk = data[:min(len(data), 1000)]
            if not chunk:
                chunk = os.urandom(100)

            fuzz_arrow_get(chunk)
            fuzz_arrow_factory(chunk)
            fuzz_arrow_format(chunk)
            fuzz_arrow_properties(chunk)

            if iteration - last_report >= 10000:
                msg = f"Arrow fuzzer: {iteration + 1} iterations completed\n"
                if log_file != '/dev/stdout':
                    with open(log_file, 'a') as f:
                        f.write(msg)
                else:
                    sys.stderr.write(msg)
                last_report = iteration

        except KeyboardInterrupt:
            break
        except Exception:
            pass

    msg = f"Arrow fuzzer: Completed {iteration + 1} iterations\n"
    if log_file != '/dev/stdout':
        with open(log_file, 'a') as f:
            f.write(msg)
    else:
        sys.stderr.write(msg)


if __name__ == '__main__':
    main()
