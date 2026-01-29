"""
Fuzz driver for Black library - Python code formatter.
Coverage-guided fuzzing using atheris/pythonfuzz pattern.
"""

import sys

# Add black source to path
sys.path.insert(0, '/app/black/src')

import black
from black import Mode, TargetVersion, format_file_contents
from black.parsing import ASTSafetyError, InvalidInput
from black.report import NothingChanged


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


def fuzz_format_basic(data: bytes) -> None:
    """Fuzz basic code formatting."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)
    mode = Mode()

    try:
        result = format_file_contents(src, mode=mode, fast=True)
    except (NothingChanged, InvalidInput, SyntaxError, ASTSafetyError, RecursionError):
        pass


def fuzz_format_with_mode(data: bytes) -> None:
    """Fuzz formatting with different modes."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)

    # Test different target versions
    modes = [
        Mode(target_versions={TargetVersion.PY310}),
        Mode(target_versions={TargetVersion.PY311}),
        Mode(target_versions={TargetVersion.PY312}),
    ]

    for mode in modes:
        try:
            result = format_file_contents(src, mode=mode, fast=True)
        except (NothingChanged, InvalidInput, SyntaxError, ASTSafetyError, RecursionError):
            pass


def fuzz_format_str(data: bytes) -> None:
    """Fuzz format_str function."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)
    mode = Mode()

    try:
        result = black.format_str(src, mode=mode)
    except (SyntaxError, RecursionError, ValueError):
        pass


def fuzz_modes_and_features(data: bytes) -> None:
    """Fuzz different mode configurations."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)

    # Test various mode configurations
    modes = [
        Mode(),
        Mode(is_pyi=True),
        Mode(magic_trailing_comma=False),
    ]

    for mode in modes:
        try:
            result = format_file_contents(src, mode=mode, fast=True)
        except (NothingChanged, InvalidInput, SyntaxError, ASTSafetyError, RecursionError):
            pass


def fuzz_ast_parsing(data: bytes) -> None:
    """Fuzz AST parsing functions."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)

    try:
        from black.parsing import lib2to3_parse, parse_ast
        tree = lib2to3_parse(src)
        _ = parse_ast(src)
    except (InvalidInput, SyntaxError, RecursionError, MemoryError):
        pass


def fuzz_node_operations(data: bytes) -> None:
    """Fuzz node operations."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)

    try:
        from black.parsing import lib2to3_parse, stringify_ast
        tree = lib2to3_parse(src)
        result = stringify_ast(tree)
    except (InvalidInput, SyntaxError, RecursionError):
        pass


def fuzz_string_normalization(data: bytes) -> None:
    """Fuzz string normalization."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)

    try:
        from black.strings import normalize_string_prefix, normalize_string_quotes
        result = normalize_string_prefix(src)
    except (ValueError, TypeError):
        pass


def fuzz_edge_cases(data: bytes) -> None:
    """Test edge cases."""
    if not validate_utf8(data):
        return

    src = safe_unicode_decode(data)
    mode = Mode()

    # Empty strings
    try:
        format_file_contents('', mode=mode, fast=True)
    except (NothingChanged, InvalidInput):
        pass

    # Whitespace only
    try:
        format_file_contents('   \n\t\n   ', mode=mode, fast=True)
    except (NothingChanged, InvalidInput):
        pass

    # Comments
    try:
        format_file_contents(src, mode=mode, fast=True)
    except (NothingChanged, InvalidInput, SyntaxError, ASTSafetyError):
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
    fuzz_format_basic(data)
    fuzz_format_with_mode(data)
    fuzz_format_str(data)
    fuzz_modes_and_features(data)
    fuzz_ast_parsing(data)
    fuzz_node_operations(data)
    fuzz_string_normalization(data)
    fuzz_edge_cases(data)


if __name__ == '__main__':
    main()
