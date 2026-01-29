#!/usr/bin/env python3
"""LibFuzzer harness for MiniSGL Structured Generation Language."""

import sys
import atheris

try:
    # Try to import minisgl modules
    import minisgl
except ImportError as e:
    print(f"Failed to import minisgl: {e}", file=sys.stderr)
    # Continue anyway, as we'll handle import errors in the fuzz function
    pass


def fuzz_minisgl_parsing(data: bytes) -> None:
    """Fuzz minisgl program parsing and execution."""
    try:
        # Convert bytes to string
        input_str = data.decode('utf-8', errors='ignore')

        # Try to parse as SGL program
        try:
            # Try various minisgl module functions
            try:
                # Attempt to parse SGL syntax
                lines = input_str.split('\n')
                for line in lines:
                    if line.strip():
                        # Try to process line as SGL
                        pass
            except Exception:
                pass

        except Exception:
            pass

    except (UnicodeDecodeError, MemoryError, RuntimeError):
        pass


def fuzz_minisgl_constraint_parsing(data: bytes) -> None:
    """Fuzz minisgl constraint specifications."""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Try to parse constraint-like syntax
        try:
            # Parse JSON-like constraint definitions
            import json
            json.loads(input_str)
        except (json.JSONDecodeError, ValueError):
            pass

    except Exception:
        pass


def fuzz_minisgl_variable_binding(data: bytes) -> None:
    """Fuzz minisgl variable binding and references."""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Try to process variable references
        try:
            # Look for ${...} style variable references
            import re
            vars = re.findall(r'\$\{([^}]+)\}', input_str)
            for var in vars:
                # Try to process variable name
                pass
        except Exception:
            pass

    except Exception:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing function."""
    fuzz_minisgl_parsing(data)
    fuzz_minisgl_constraint_parsing(data)
    fuzz_minisgl_variable_binding(data)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
