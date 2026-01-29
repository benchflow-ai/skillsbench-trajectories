#!/usr/bin/env python3
"""
Fuzz driver for Black library
Fuzzes Python code formatting functions
"""
import sys
import random
import string
import black
from black.report import NothingChanged


def generate_random_python_code():
    """Generate random Python-like code for fuzzing"""
    # Generate code dynamically to avoid issues with f-strings in templates
    choice = random.randint(0, 20)

    if choice == 0:
        return ''
    elif choice == 1:
        return ' ' * random.randint(0, 20)
    elif choice == 2:
        return '\n' * random.randint(1, 10)
    elif choice == 3:
        return 'x = 1'
    elif choice == 4:
        return 'def f(): pass'
    elif choice == 5:
        return 'class C: pass'
    elif choice == 6:
        return 'import os'
    elif choice == 7:
        return 'from sys import argv'
    elif choice == 8:
        return f'def func_{random.randint(1, 100)}():\n    pass'
    elif choice == 9:
        return f'def func_with_args(a,b,c):\n    return a+b+c'
    elif choice == 10:
        return f'lambda x: x+{random.randint(1, 100)}'
    elif choice == 11:
        return '[x for x in range(10)]'
    elif choice == 12:
        return '{x:x*10 for x in range(10)}'
    elif choice == 13:
        return '(x for x in range(10))'
    elif choice == 14:
        return 'def '  # Incomplete function
    elif choice == 15:
        return 'if '   # Incomplete if
    elif choice == 16:
        return 'for i in'  # Incomplete for
    elif choice == 17:
        return 'class '  # Incomplete class
    elif choice == 18:
        return '=' * random.randint(1, 100)
    elif choice == 19:
        return ''.join(random.choices(string.ascii_letters + string.digits + '\n\r\t ', k=random.randint(0, 500)))
    else:
        # Remaining cases
        remaining_choices = [
            '🎉' * random.randint(0, 50),
            '# Comment with émojis 🎨\ncode = "test"',
            '"unicode: 你好 мир"',
            '\x00\x01\x02',  # Control characters
            'x = ' + '1' * random.randint(100, 1000),
            '[' * random.randint(1, 50) + ']' * random.randint(1, 50),
            'def f(\n',  # Unclosed parenthesis
            'def f()\n    ',  # Incomplete
            'if x\n    y = 1',  # Missing colon
            'for i in\n    pass',  # Missing iterable
            '1 + + 1',  # Double operator
            '1 + + + 1',  # Triple operator
        ]
        return random.choice(remaining_choices)


def fuzz_format_str():
    """Fuzz the format_str() function"""
    for _ in range(200):
        code = generate_random_python_code()
        target_versions_list = [
            black.TargetVersion.PY36,
            black.TargetVersion.PY37,
            black.TargetVersion.PY38,
            black.TargetVersion.PY39,
            black.TargetVersion.PY310,
            black.TargetVersion.PY311,
        ]
        num_versions = min(random.randint(1, 3), len(target_versions_list))
        mode = black.Mode(
            line_length=random.choice([80, 100, 120]),
            target_versions=set(random.sample(target_versions_list, num_versions)),
            string_normalization=random.choice([True, False]),
            is_pyi=random.choice([True, False]),
        )

        try:
            result = black.format_str(code, mode=mode)
            assert isinstance(result, str)
        except black.InvalidInput as e:
            # Expected for invalid Python syntax
            pass
        except Exception as e:
            print(f"Unexpected error in format_str: {e}", file=sys.stderr)
            raise


def fuzz_lib2to3_parse():
    """Fuzz the lib2to3_parse() function"""
    from black.parsing import lib2to3_parse, InvalidInput

    for _ in range(100):
        code = generate_random_python_code()
        target_versions_list = [
            black.TargetVersion.PY36,
            black.TargetVersion.PY37,
            black.TargetVersion.PY38,
            black.TargetVersion.PY39,
            black.TargetVersion.PY310,
            black.TargetVersion.PY311,
        ]
        num_versions = min(random.randint(1, 3), len(target_versions_list))
        target_versions = set(random.sample(target_versions_list, num_versions))

        try:
            result = lib2to3_parse(code, target_versions=target_versions)
            assert result is not None
        except InvalidInput as e:
            # Expected for invalid Python syntax
            pass
        except Exception as e:
            print(f"Unexpected error in lib2to3_parse: {e}", file=sys.stderr)
            raise


def fuzz_format_file_contents():
    """Fuzz the format_file_contents() function"""
    for _ in range(100):
        code = generate_random_python_code()
        mode = black.Mode(
            line_length=random.choice([80, 100]),
            string_normalization=random.choice([True, False]),
        )

        try:
            result = black.format_file_contents(code, fast=random.choice([True, False]), mode=mode)
            assert isinstance(result, str)
        except (black.InvalidInput, NothingChanged) as e:
            # Expected for invalid Python syntax or no changes
            pass
        except Exception as e:
            print(f"Unexpected error in format_file_contents: {e}", file=sys.stderr)
            raise


if __name__ == '__main__':
    print("Starting Black fuzzing...")
    fuzz_format_str()
    print("✓ format_str() fuzzed successfully")
    fuzz_lib2to3_parse()
    print("✓ lib2to3_parse() fuzzed successfully")
    fuzz_format_file_contents()
    print("✓ format_file_contents() fuzzed successfully")
    print("Black fuzzing completed successfully!")
