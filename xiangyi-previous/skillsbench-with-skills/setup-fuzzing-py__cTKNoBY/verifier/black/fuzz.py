#!/usr/bin/env python3
"""Coverage-guided fuzzer for Black code formatter using atheris."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for black.format_str() function."""
    try:
        import black
        from black import Mode, TargetVersion
        from black.parsing import InvalidInput
        from blib2to3.pgen2.tokenize import TokenizerError
        
        # Convert bytes to string
        try:
            source_code = data.decode('utf-8')
        except UnicodeDecodeError:
            source_code = data.decode('latin-1')
        
        # Test format_str with default mode
        try:
            black.format_str(source_code, mode=Mode())
        except (InvalidInput, TokenizerError, IndentationError, 
                SyntaxError, ValueError, AssertionError):
            pass
        
        # Test with different target versions
        if len(data) > 0:
            version_idx = data[0] % 6
            versions = [
                {TargetVersion.PY38},
                {TargetVersion.PY39},
                {TargetVersion.PY310},
                {TargetVersion.PY311},
                {TargetVersion.PY312},
                set(),
            ]
            try:
                mode = Mode(
                    target_versions=versions[version_idx],
                    line_length=88 if len(data) < 2 else (data[1] % 200) + 1,
                )
                black.format_str(source_code, mode=mode)
            except (InvalidInput, TokenizerError, IndentationError,
                    SyntaxError, ValueError, AssertionError):
                pass
                
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
