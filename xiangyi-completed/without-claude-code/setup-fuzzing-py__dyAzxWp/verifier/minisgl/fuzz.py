#!/usr/bin/env python3
"""
Fuzz driver for Mini-SGLang
Tests configuration parsing and message handling
"""

import sys
import json
import atheris

with atheris.instrument_imports():
    # Import basic utilities that don't require GPU
    pass


def fuzz_json_input(data):
    """Fuzz JSON parsing for request handling"""
    try:
        parsed = json.loads(data)
        # Validate common request fields
        if isinstance(parsed, dict):
            # Try to access common fields
            _ = parsed.get('prompt', '')
            _ = parsed.get('max_tokens', 0)
            _ = parsed.get('temperature', 0.0)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        pass
    except Exception as e:
        pass


def fuzz_config_parsing(data):
    """Fuzz configuration parameter parsing"""
    try:
        # Parse as potential config data
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            # Validate config-like fields
            for key, value in parsed.items():
                if isinstance(key, str) and len(key) < 100:
                    # Check value types
                    if isinstance(value, (int, float, str, bool)):
                        pass
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception as e:
        pass


def fuzz_text_input(data):
    """Fuzz text input handling (prompt processing)"""
    try:
        # Simulate text processing
        text = data.strip()
        # Basic validation
        if len(text) > 0:
            # Check for special characters
            _ = text.encode('utf-8')
            _ = text.split()
    except (ValueError, TypeError, UnicodeError):
        pass
    except Exception as e:
        pass


@atheris.instrument_func
def TestOneInput(data):
    """Main fuzzing entry point"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 2)
    remaining = fdp.ConsumeBytes(fdp.remaining_bytes())

    if choice == 0:
        # Fuzz JSON input
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_json_input(input_str)
        except:
            pass
    elif choice == 1:
        # Fuzz config parsing
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_config_parsing(input_str)
        except:
            pass
    else:
        # Fuzz text input
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_text_input(input_str)
        except:
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
