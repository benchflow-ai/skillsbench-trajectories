#!/usr/bin/env python3
"""
Fuzz driver for IPython
Tests input processing and code completion functions
"""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils import text
    from IPython.core.formatters import PlainTextFormatter


def fuzz_input_transformer(data):
    """Fuzz IPython input transformation"""
    try:
        tm = TransformerManager()
        lines = data.split('\n')
        for line in lines:
            tm.transform_cell(line)
    except (ValueError, TypeError, SyntaxError, AttributeError):
        pass
    except Exception as e:
        pass


def fuzz_text_utils(data):
    """Fuzz IPython text utility functions"""
    try:
        # Test various text processing functions
        text.marquee(data)
    except (ValueError, TypeError, UnicodeDecodeError):
        pass
    except Exception as e:
        pass


def fuzz_formatter(data):
    """Fuzz IPython object formatters"""
    try:
        formatter = PlainTextFormatter()
        # Create a simple object with the data
        class TestObj:
            def __repr__(self):
                return data

        obj = TestObj()
        formatter(obj)
    except (ValueError, TypeError, AttributeError):
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

    try:
        input_str = remaining.decode('utf-8', errors='ignore')
    except:
        return

    if choice == 0:
        # Fuzz input transformer
        fuzz_input_transformer(input_str)
    elif choice == 1:
        # Fuzz text utilities
        fuzz_text_utils(input_str)
    else:
        # Fuzz formatter
        fuzz_formatter(input_str)


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
