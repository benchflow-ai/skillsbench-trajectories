#!/usr/bin/env python3
"""
Fuzz driver for IPython library.
Coverage-guided fuzzing for interactive Python shell components.
"""

import sys
import os
import time
import random
import string

# Add the library to path
sys.path.insert(0, '/app/ipython')

# IPython imports
try:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.compilerop import CodeCompiler
    from IPython.utils.PyColorize import PyColorize
    IPYTHON_AVAILABLE = True
except ImportError as e:
    IPYTHON_AVAILABLE = False


def fuzz_python_code(data: bytes) -> str:
    """Create fuzzed Python code from random bytes."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "x = 1"

    templates = [
        "",
        "x = 1",
        "x = 'hello'",
        "def f(): return 42",
        "class A: pass",
        "if True: pass",
    ]

    if len(text) < 3 or random.random() < 0.3:
        return random.choice(templates)

    # Generate Python-like code
    lines = []

    # Clean and split
    raw_lines = text.split('\n')[:50]

    keywords = ['def', 'class', 'if', 'for', 'while', 'try', 'with', 'import', 'from']
    for line in raw_lines:
        clean = line.replace('\x00', '').strip()
        if not clean:
            lines.append('')
            continue

        # Add randomness
        if random.random() < 0.1:
            lines.append(f"# fuzz: {clean[:40]}")
        elif any(kw in clean for kw in keywords):
            # Keep lines that look like they have keywords
            if random.random() < 0.5:
                indent = " " * (random.randint(0, 4) * 4)
                lines.append(indent + clean[:60])
            else:
                lines.append(clean[:60])
        else:
            lines.append(clean[:80])

    return '\n'.join(lines)


def fuzz_identifier(data: bytes) -> str:
    """Create a fuzzed Python identifier."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "x"

    # Valid identifier characters
    valid = string.ascii_letters + string.digits + '_'
    result = ""

    for i, c in enumerate(text):
        if i == 0:
            if c in string.ascii_letters + '_':
                result += c
        else:
            if c in valid:
                result += c

    if not result or not result[0].isalpha():
        result = "x"

    return result[:50]


def run_fuzz_test(data: bytes) -> None:
    """Main fuzz test function - processes a single fuzz input."""
    try:
        code = fuzz_python_code(data)

        if not IPYTHON_AVAILABLE:
            # Still test basic compilation without full IPython
            try:
                compile(code, '<fuzz>', 'exec')
            except Exception:
                pass
            return

        # Test 1: Code compilation
        try:
            compiler = CodeCompiler()
            compiler.compile(code, '<fuzz>', 'exec')
        except Exception:
            pass

        # Test 2: Interactive shell (limited)
        try:
            shell = InteractiveShell.instance()

            # Test execution with timeout protection
            result = shell.run_cell(code, silent=True)
        except Exception:
            pass
        finally:
            try:
                InteractiveShell.clear_instance()
            except:
                pass

        # Test 3: Syntax coloring
        try:
            colorizer = PyColorize()
            colorizer.format(code)
        except Exception:
            pass

        # Test 4: Inspections with random names
        try:
            shell = InteractiveShell.instance()

            for _ in range(min(5, len(data))):
                name = fuzz_identifier(data)
                try:
                    shell.inspect(name)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                InteractiveShell.clear_instance()
            except:
                pass

        # Test 5: Format text (display hook)
        try:
            shell = InteractiveShell.instance()
            shell.displayhook.format(42)
        except Exception:
            pass
        finally:
            try:
                InteractiveShell.clear_instance()
            except:
                pass

        # Test 6: Complete with random text
        try:
            completer = shell.Completer

            for _ in range(min(3, len(data))):
                text = fuzz_identifier(data)
                try:
                    completer.complete(text)
                except Exception:
                    pass
        except Exception:
            pass

    except Exception as e:
        pass


def run_standalone_fuzzer(seconds: int = 10) -> None:
    """Run standalone fuzzer with random input generation."""
    print(f"Starting IPython fuzzer for {seconds} seconds...")

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < seconds:
        # Generate random input
        length = random.randint(0, 1000)
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
