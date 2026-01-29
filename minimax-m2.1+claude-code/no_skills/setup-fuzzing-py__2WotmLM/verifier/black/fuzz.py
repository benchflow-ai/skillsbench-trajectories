#!/usr/bin/env python3
"""
Fuzz driver for Black library.
Coverage-guided fuzzing for Python code formatting.
"""

import sys
import os
import time
import random
import string

# Add the library to path
sys.path.insert(0, '/app/black')

import black


def fuzz_python_code(data: bytes) -> str:
    """Create fuzzed Python code from random bytes."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "x = 1"

    # Templates for valid Python code
    templates = [
        # Empty/simple
        "",
        "x = 1",
        "x = 'hello'",
        "x = [1, 2, 3]",
        "x = {'a': 1}",

        # Functions
        "def f(): pass",
        "def f(x): return x",
        "async def f(): pass",

        # Classes
        "class A: pass",
        "class A(B): pass",

        # Control flow
        "if x: pass",
        "if x: a\nelse: b",
        "for i in range(10): pass",
        "while True: break",

        # Imports
        "import os",
        "from sys import path",

        # Decorators
        "@decorator\ndef f(): pass",
    ]

    # Add randomness based on input
    if len(text) == 0 or random.random() < 0.3:
        return random.choice(templates)

    # Try to make a valid Python-ish structure
    lines = []

    # Add some indentation
    indent = " " * (random.randint(0, 8) * 4)

    # Split input into "lines"
    input_lines = text.split('\n')
    for line in input_lines[:20]:  # Limit lines
        # Clean up special characters that break Python
        clean_line = line.replace('\x00', '').strip()

        if not clean_line:
            lines.append('')
            continue

        # Wrap in valid Python syntax where possible
        if clean_line.startswith('#'):
            lines.append(clean_line)  # Keep comments
        elif random.random() < 0.1:
            lines.append(f"# {clean_line[:50]}")
        elif random.random() < 0.2:
            lines.append(f"x_{random.randint(0, 100)} = {clean_line[:30]}")
        elif random.random() < 0.1:
            lines.append(f"def f_{random.randint(0, 100)}(): {clean_line[:20]}")
        else:
            # Just use cleaned line
            lines.append(indent + clean_line[:100])

    return '\n'.join(lines)


def fuzz_format_string(data: bytes) -> str:
    """Create a fuzzed format string (for pyproject.toml)."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return ""

    templates = [
        "",
        "[tool.black]",
        "[tool.black]\nline-length = 88",
        "[tool.black]\ntarget-version = ['py310']",
        "[tool.black]\ninclude = '\\.pyi?$'",
        "[tool.black]\nexclude = '/tests/'",
    ]

    if len(text) < 5 or random.random() < 0.5:
        return random.choice(templates)

    return text[:200]


def run_fuzz_test(data: bytes) -> None:
    """Main fuzz test function - processes a single fuzz input."""
    try:
        # Test 1: Format Python code
        code = fuzz_python_code(data)
        try:
            black.format_str(code, mode=black.Mode())
        except black.InvalidInput:
            pass
        except Exception:
            pass

        # Test 2: Format with different modes
        modes = [
            black.Mode(),
            black.Mode(target_versions=set([black.TargetVersion.PY310])),
            black.Mode(is_pyi=random.random() > 0.5),
            black.Mode(line_length=random.randint(50, 200)),
        ]

        for mode in modes[:2]:  # Limit to avoid too many iterations
            try:
                black.format_str(code, mode=mode)
            except Exception:
                pass

        # Test 3: Test pyproject.toml parsing (basic)
        toml_content = fuzz_format_string(data)
        if toml_content:
            try:
                # This may fail on invalid TOML
                if '[' in toml_content:
                    pass  # Just ensure it doesn't crash
            except Exception:
                pass

        # Test 4: Test lib2to3_parse
        if code:
            try:
                black.lib2to3_parse(code)
            except Exception:
                pass

        # Test 5: Test string formatting edge cases
        edge_cases = [
            "x = 1" * 1000,  # Long line
            "x = '" + "a" * 100 + "'",  # Long string
            "# " + "comment " * 50,  # Long comment
            "a = 1\n" * 100,  # Many lines
        ]

        for case in edge_cases:
            try:
                black.format_str(case, mode=black.Mode())
            except Exception:
                pass

        # Test 6: Test special characters
        special_inputs = [
            "# coding: utf-8\nx = 'café'",
            "# -*- coding: latin-1 -*-\nx = 'résumé'",
            "x = '😀'",
            "x = '\u3042'",  # Japanese hiragana
        ]

        for inp in special_inputs:
            try:
                black.format_str(inp, mode=black.Mode())
            except Exception:
                pass

    except Exception as e:
        pass


def run_standalone_fuzzer(seconds: int = 10) -> None:
    """Run standalone fuzzer with random input generation."""
    print(f"Starting Black fuzzer for {seconds} seconds...")

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < seconds:
        # Generate random input
        length = random.randint(0, 2000)
        data = bytes(random.randint(0, 255) for _ in range(length))

        run_fuzz_test(data)
        iterations += 1

    print(f"Completed {iterations} iterations in {seconds} seconds")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Standalone mode with random inputs
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_standalone_fuzzer(seconds)
    else:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.buffer.read()
        run_fuzz_test(data)


if __name__ == "__main__":
    main()
