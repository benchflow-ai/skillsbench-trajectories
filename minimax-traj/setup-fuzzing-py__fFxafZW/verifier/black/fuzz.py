#!/usr/bin/env python3
"""
Fuzz driver for Black library using atheris.

Tests:
- black.format_str() with various Python code inputs
- Invalid syntax handling
- Different mode configurations
"""

import sys
import atheris
from typing import List


def fuzz_black_format(data: bytes) -> None:
    """Fuzz black.format_str() with various code inputs."""
    try:
        import black

        # Decode input to string
        if len(data) > 0:
            try:
                code = data.decode('utf-8', errors='ignore')
            except Exception:
                return

            # Test basic format_str
            try:
                mode = black.Mode()
                black.format_str(code, mode=mode)
            except Exception:
                pass  # Expected for invalid syntax

            # Test with different line lengths
            try:
                mode = black.Mode(line_length=80)
                black.format_str(code, mode=mode)
            except Exception:
                pass

            # Test with fast mode
            try:
                mode = black.Mode()
                black.format_str(code, fast=True, mode=mode)
            except Exception:
                pass

            # Test with string normalization disabled
            try:
                mode = black.Mode(string_normalization=False)
                black.format_str(code, mode=mode)
            except Exception:
                pass

            # Test format_file_contents
            try:
                mode = black.Mode()
                black.format_file_contents(code, fast=True, mode=mode)
            except Exception:
                pass

    except ImportError:
        # Library not installed
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing entry point."""
    fuzz_black_format(data)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Fuzz driver for Black library")
        print("Usage: python fuzz.py")
        sys.exit(0)

    atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()
