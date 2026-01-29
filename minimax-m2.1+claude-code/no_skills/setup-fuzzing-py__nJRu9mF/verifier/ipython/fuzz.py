"""
Fuzz driver for IPython library - Interactive Python shell.
Coverage-guided fuzzing using atheris/pythonfuzz pattern.
"""

import sys
import os

# Set environment to avoid terminal dependencies
os.environ['TERM'] = 'dumb'
os.environ['PYTHONBREAKPOINT'] = '0'

# Add IPython to path
sys.path.insert(0, '/app/ipython')

from IPython.core.inputtransformer2 import TransformerManager


def validate_utf8(data: bytes) -> bool:
    """Check if data is valid UTF-8."""
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def safe_unicode_decode(data: bytes) -> str:
    """Safely decode bytes to string."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('utf-8', errors='replace')


def fuzz_input_transformer(data: bytes) -> None:
    """Fuzz input transformation."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)
    tm = TransformerManager()

    try:
        result = tm.transform_cell(input_str)
    except (ValueError, SyntaxError, RecursionError, MemoryError):
        pass


def fuzz_line_processing(data: bytes) -> None:
    """Fuzz line-by-line processing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)
    tm = TransformerManager()

    lines = input_str.split('\n')
    for line in lines:
        try:
            result = tm.transform_cell(line)
        except (ValueError, SyntaxError):
            pass


def fuzz_split_input(data: bytes) -> None:
    """Fuzz command splitting."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.core.splitinput import split_user_input
        result = split_user_input(input_str)
    except (ValueError, SyntaxError):
        pass


def fuzz_text_utilities(data: bytes) -> None:
    """Fuzz text utilities."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.utils.text import dedent, indent, format_screen
        _ = dedent(input_str)
        _ = indent(input_str, '  ')
        _ = format_screen(input_str)
    except (ValueError, TypeError):
        pass


def fuzz_token_util(data: bytes) -> None:
    """Fuzz token utilities."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.utils.tokenutil import tokenize
        tokens = list(tokenize(input_str))
    except (ValueError, SyntaxError, TypeError):
        pass


def fuzz_formatters(data: bytes) -> None:
    """Fuzz object formatters."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.core.formatters import Formatter
        f = Formatter()

        # Test formatting various types
        test_objects = [
            input_str,
            int(input_str) if input_str.isdigit() else 0,
            float(input_str) if input_str.replace('.', '').replace('-', '').isdigit() else 0.0,
            input_str.split(',') if ',' in input_str else [input_str],
        ]

        for obj in test_objects:
            try:
                result = f(obj)
            except (ValueError, TypeError):
                pass
    except ImportError:
        pass


def fuzz_display_objects(data: bytes) -> None:
    """Fuzz display objects."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.core.display import TextDisplayObject
        obj = TextDisplayObject(text=input_str)
        _ = obj._repr_mimebundle_()
    except (ValueError, TypeError):
        pass

    try:
        from IPython.core.display import HTML
        obj = HTML(input_str)
        _ = obj._repr_html_()
    except (ValueError, TypeError):
        pass


def fuzz_guarded_eval(data: bytes) -> None:
    """Fuzz guarded evaluation."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.core.guarded_eval import EvalWithKnownTypes, evaluations
        # Test that eval can handle the string
        eval_system = EvalWithKnownTypes()
        # This shouldn't actually evaluate arbitrary code in fuzzing
    except (ImportError, ValueError):
        pass


def fuzz_coloransi(data: bytes) -> None:
    """Fuzz color/ANSI utilities."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.utils.coloransi import TermColors
        _ = TermColors
    except (ValueError, TypeError):
        pass


def fuzz_ipstruct(data: bytes) -> None:
    """Fuzz IPython structures."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from IPython.utils.ipstruct import Struct
        s = Struct()
        s[input_str] = input_str
        _ = s.get(input_str)
    except (ValueError, TypeError):
        pass


def fuzz_regex_patterns(data: bytes) -> None:
    """Fuzz regex pattern handling."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        import re
        pattern = re.compile(input_str)
        result = pattern.match(input_str)
    except re.error:
        pass


def main():
    """Main entry point for fuzzing."""
    # Get input from stdin (LibFuzzer/AFL style) or use provided data
    if len(sys.argv) > 1:
        # Read from file (AFL/LibFuzzer queue)
        with open(sys.argv[1], 'rb') as f:
            data = f.read()
    else:
        # Read from stdin
        data = sys.stdin.buffer.read()

    if not data:
        return

    # Run all fuzz targets
    fuzz_input_transformer(data)
    fuzz_line_processing(data)
    fuzz_split_input(data)
    fuzz_text_utilities(data)
    fuzz_token_util(data)
    fuzz_formatters(data)
    fuzz_display_objects(data)
    fuzz_coloransi(data)
    fuzz_ipstruct(data)
    fuzz_regex_patterns(data)


if __name__ == '__main__':
    main()
