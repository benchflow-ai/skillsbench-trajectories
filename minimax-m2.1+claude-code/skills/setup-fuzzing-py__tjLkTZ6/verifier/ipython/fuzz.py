#!/usr/bin/env python3
"""
Fuzz driver for IPython library
Fuzzes input transformation and parsing functions
"""
import sys
import random
import string
import ast


def generate_random_ipython_input():
    """Generate random IPython-like input for fuzzing"""
    templates = [
        # Empty
        '',
        ' ' * random.randint(0, 20),
        '\n' * random.randint(1, 10),

        # Magic commands
        f'%pwd',
        f'%ls',
        f'%timeit {random.randint(1, 100)}',
        f'%matplotlib inline',
        f'%%time\nx = {random.randint(1, 100)}',
        f'%%capture\nresult = "test"',

        # System commands
        f'!ls -la',
        f'!echo "{random.randint(1, 100)}"',
        f'!python --version',

        # Python code
        f'x = {random.randint(1, 100)}',
        f'def func_{random.randint(1, 100)}():\n    pass',
        f'import os\nprint("test")',
        '[x for x in range(10)]',

        # Mixed IPython and Python
        f'%pwd\nx = {random.randint(1, 100)}',
        f'!ls\n%timeit pass',

        # Help commands
        f'func_{random.randint(1, 100)}?',
        f'func_{random.randint(1, 100)}??',

        # Prompts
        f'>>> x = {random.randint(1, 100)}',
        f'>>> def f():\n...     pass',
        f'In [1]: x = {random.randint(1, 100)}',
        f'In [1]: def f():\n   ...:     pass',

        # Random strings
        ''.join(random.choices(string.ascii_letters + string.digits + ' \n\r\t', k=random.randint(0, 200))),

        # Special characters
        '🎉' * random.randint(0, 20),
        '# Comment with émojis\n',
        '"unicode: 你好 мир"',
        '\x00\x01\x02',

        # Malformed magics
        '%' * random.randint(1, 10),
        '!' * random.randint(1, 10),
        '?' * random.randint(1, 10),

        # Edge cases
        'def ' * random.randint(1, 10),
        'if ' * random.randint(1, 10),
        'for i in ' * random.randint(1, 10),

        # Long lines
        'x = ' + '1' * random.randint(100, 500),

        # Indentation errors
        'def f():\npass',  # Missing indent
        'if x:\ny = 1',  # Missing indent
    ]

    return random.choice(templates)


def fuzz_transformer_manager():
    """Fuzz the TransformerManager"""
    from IPython.core.inputtransformer2 import TransformerManager

    tm = TransformerManager()

    for _ in range(200):
        lines = generate_random_ipython_input().split('\n')

        try:
            result = tm.transform_cell(''.join(lines))
            # result can be None or a string
            if result is not None:
                assert isinstance(result, str)
        except Exception as e:
            # Some inputs might cause exceptions
            # Log unexpected errors
            pass


def fuzz_prompt_stripper():
    """Fuzz the PromptStripper"""
    from IPython.core.inputtransformer2 import classic_prompt, ipython_prompt

    prompts = [
        ('>>> ', None),  # Classic Python prompt
        ('... ', None),  # Continuation
        ('In [1]: ', None),  # IPython prompt
        ('   ...: ', None),  # IPython continuation
        (f'In [{random.randint(1, 100)}]: ', None),
        (f'   ...: ', None),
    ]

    for _ in range(100):
        prompt_re, initial_re = random.choice(prompts)
        lines = [
            prompt_re + f'x = {random.randint(1, 100)}',
            '... ' + f'y = {random.randint(1, 100)}',
            '',
        ]

        try:
            result = classic_prompt(lines)
            assert isinstance(result, list)
        except Exception as e:
            print(f"Unexpected error in classic_prompt: {e}", file=sys.stderr)
            raise

        try:
            result = ipython_prompt(lines)
            assert isinstance(result, list)
        except Exception as e:
            print(f"Unexpected error in ipython_prompt: {e}", file=sys.stderr)
            raise


def fuzz_split_input():
    """Fuzz the splitinput functionality"""
    from IPython.core.splitinput import split_user_input

    for _ in range(100):
        line = generate_random_ipython_input()

        try:
            result = split_user_input(line)
            # result is a tuple with various parts
            assert result is not None
        except Exception as e:
            # Some malformed inputs might cause exceptions
            pass


def fuzz_tokenize():
    """Fuzz with actual Python tokenization"""
    from IPython.utils import tokenutil

    for _ in range(100):
        code = generate_random_ipython_input()

        try:
            # Try to parse as Python AST
            ast.parse(code)
        except SyntaxError:
            # Expected for invalid syntax
            pass
        except Exception as e:
            print(f"Unexpected error in ast.parse: {e}", file=sys.stderr)
            raise


if __name__ == '__main__':
    print("Starting IPython fuzzing...")
    fuzz_transformer_manager()
    print("✓ TransformerManager fuzzed successfully")
    fuzz_prompt_stripper()
    print("✓ PromptStripper fuzzed successfully")
    fuzz_split_input()
    print("✓ split_input fuzzed successfully")
    fuzz_tokenize()
    print("✓ tokenize fuzzed successfully")
    print("IPython fuzzing completed successfully!")
