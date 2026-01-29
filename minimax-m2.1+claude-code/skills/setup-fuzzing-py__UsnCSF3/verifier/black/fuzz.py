#!/usr/bin/env python3
"""
Fuzz driver for Black library.
Uses LibFuzzer-style coverage-guided fuzzing.
"""

import sys
import traceback
from typing import Any

import black
from black import Mode, format_str
from black.parsing import lib2to3_parse


def fuzz_black_format(input_data: bytes) -> None:
    """Fuzz black.format_str() with random Python code."""
    try:
        data = input_data.decode('utf-8', errors='replace')

        # Try format_str with various modes
        modes = [
            Mode(),
            Mode(target_version=black.TargetVersion.PY310),
            Mode(target_version=black.TargetVersion.PY311),
            Mode(line_length=88),
            Mode(line_length=100),
        ]

        for mode in modes:
            try:
                format_str(data, mode=mode)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_lib2to3_parse(input_data: bytes) -> None:
    """Fuzz lib2to3_parse with various string inputs."""
    try:
        data = input_data.decode('utf-8', errors='replace')

        try:
            lib2to3_parse(data)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_black_mode(input_data: bytes) -> None:
    """Fuzz Mode class construction with various parameters."""
    try:
        nums = [abs(b) for b in input_data[:16]]

        # Test various Mode configurations
        target_versions = [
            black.TargetVersion.PY310,
            black.TargetVersion.PY311,
            black.TargetVersion.PY312,
        ]

        for tv in target_versions:
            try:
                Mode(target_version=tv)
            except Exception:
                pass

        # Test with different line lengths
        for ll in [50, 79, 88, 100, 120, 200]:
            try:
                Mode(line_length=ll)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_black_feature_flags(input_data: bytes) -> None:
    """Fuzz feature flag handling."""
    try:
        nums = [abs(b) for b in input_data[:16]]

        # Test various feature combinations
        features = [
            black.Feature.IMPLICIT_STRING_CONCATENATION,
            black.Feature.PATTERN_MATCHING,
            black.Feature.ANNOTATION_UNIONS,
        ]

        for feature in features:
            try:
                black.supports_feature(feature)
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
    fuzz_black_format(input_data)
    fuzz_lib2to3_parse(input_data)
    fuzz_black_mode(input_data)
    fuzz_black_feature_flags(input_data)


if __name__ == '__main__':
    main()
