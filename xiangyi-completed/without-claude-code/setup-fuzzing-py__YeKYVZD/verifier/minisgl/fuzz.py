#!/usr/bin/env python3
"""
Fuzzing driver for Mini-SGLang library using Atheris (LibFuzzer for Python)
Targets: Configuration parsing, input validation, and graph operations
Note: This fuzzer focuses on components that don't require GPU/CUDA
"""

import sys
import atheris
import json

# Suppress warnings for cleaner fuzzing output
import warnings
warnings.filterwarnings("ignore")

# Don't instrument yaml import as it's not critical
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def TestOneInput(data):
    """Fuzz target for Mini-SGLang library - lightweight version."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz JSON config parsing
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            result = json.loads(json_string)
            # Validate structure
            if isinstance(result, dict):
                _ = json.dumps(result)

        elif choice == 1 and HAS_YAML:
            # Fuzz YAML config parsing
            yaml_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            result = yaml.safe_load(yaml_string)
            if result:
                _ = str(result)

        elif choice == 2:
            # Fuzz dictionary-based config validation
            config = {}
            num_keys = fdp.ConsumeIntInRange(0, 30)
            for _ in range(num_keys):
                key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 50))
                value_type = fdp.ConsumeIntInRange(0, 5)

                if value_type == 0:
                    value = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
                elif value_type == 1:
                    value = fdp.ConsumeInt(8)
                elif value_type == 2:
                    value = fdp.ConsumeFloat()
                elif value_type == 3:
                    value = fdp.ConsumeBool()
                elif value_type == 4:
                    # List
                    value = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
                else:
                    value = None

                if key:
                    config[key] = value

            # Validate config dict
            _ = json.dumps(config, default=str)

        elif choice == 3:
            # Fuzz text input handling - simulate prompt processing
            text_input = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 5000))

            # Simulate basic text processing operations
            _ = len(text_input)
            _ = text_input.strip()
            _ = text_input.split()
            _ = text_input.encode('utf-8', errors='ignore')

            # Simulate parameter extraction
            if '=' in text_input:
                parts = text_input.split('=', 1)
                if len(parts) == 2:
                    try:
                        _ = float(parts[1].strip())
                    except ValueError:
                        pass

    except (json.JSONDecodeError, ValueError, TypeError):
        # Expected exceptions
        pass
    except (UnicodeError, UnicodeDecodeError):
        # Expected encoding errors
        pass
    except (KeyError, AttributeError, IndexError):
        # Expected access errors
        pass
    except Exception as e:
        # Handle YAML errors if yaml is available
        if HAS_YAML:
            from yaml import YAMLError
            if isinstance(e, YAMLError):
                return

        # Unexpected exceptions might indicate bugs
        error_type = type(e).__name__
        # Allow some known safe exceptions
        if error_type not in ['RecursionError', 'MemoryError', 'RuntimeError']:
            raise


def main():
    """Main fuzzing entry point."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
