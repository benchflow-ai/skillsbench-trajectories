"""
Fuzz driver for Black library.
Focus: Python code formatting functionality
"""

import black
from black import FileMode, format_str
import time

def fuzz_black_format(data):
    """Fuzz black.format_str() with Python code"""
    try:
        code = data.decode('utf-8', errors='ignore')
        mode = FileMode()
        format_str(code, mode=mode)

        if len(code) > 0 and len(code) % 2 == 0:
            mode = FileMode(line_length=80)
            format_str(code, mode=mode)

    except black.NothingChanged:
        pass
    except (ValueError, TypeError, AttributeError, SyntaxError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_black_format: {type(e).__name__}")

def fuzz_black_lib2to3_parse(data):
    """Fuzz lib2to3_parse() with Python code"""
    try:
        code = data.decode('utf-8', errors='ignore')
        from black.parsing import lib2to3_parse
        lib2to3_parse(code, target_versions=set())
    except (ValueError, TypeError, AttributeError, SyntaxError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_black_lib2to3_parse: {type(e).__name__}")

def main():
    """Main fuzzing function"""
    test_cases = [
        b"x = 1",
        b"def foo():\n    pass",
        b"print('hello')",
        b"invalid (() code",
        b"" * 100,
        b"x = " + b"y" * 100,
        b"def f(" + b"a, " * 50 + b"z):\n    pass",
    ]

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < 10:
        for test_data in test_cases:
            choice = iterations % 2
            if choice == 0:
                fuzz_black_format(test_data)
            else:
                fuzz_black_lib2to3_parse(test_data)
            iterations += 1

    print(f"Black fuzzer: Completed {iterations} iterations in 10 seconds")

if __name__ == "__main__":
    main()
