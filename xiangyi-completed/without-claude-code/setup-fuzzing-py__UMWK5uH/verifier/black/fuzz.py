#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for Black library.
Uses atheris for coverage-guided fuzzing.
"""
import sys
import os

# Add the src path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import atheris

# Pre-import modules before instrumenting to speed up startup
import black
from black import Mode, TargetVersion
from black.parsing import lib2to3_parse, InvalidInput
from black.strings import normalize_string_quotes, normalize_string_prefix


@atheris.instrument_func
def TestOneInput(data: bytes):
    """Fuzz target for Black library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz black.format_str() - main entry point
            source = fdp.ConsumeUnicodeNoSurrogates(2048)
            line_length = fdp.ConsumeIntInRange(1, 200)
            preview = fdp.ConsumeBool()
            string_normalization = fdp.ConsumeBool()

            mode = Mode(
                line_length=line_length,
                preview=preview,
                string_normalization=string_normalization,
            )
            result = black.format_str(source, mode=mode)

            # Verify idempotency
            result2 = black.format_str(result, mode=mode)
            assert result == result2, "Formatting not idempotent"

        elif choice == 1:
            # Fuzz lib2to3_parse() - parsing engine
            source = fdp.ConsumeUnicodeNoSurrogates(2048)
            lib2to3_parse(source)

        elif choice == 2:
            # Fuzz normalize_string_quotes()
            string_input = fdp.ConsumeUnicodeNoSurrogates(256)
            if len(string_input) > 0:
                quote = fdp.PickValueInList(['"', "'", '"""', "'''"])
                test_str = f"{quote}{string_input}{quote}"
                normalize_string_quotes(test_str)

        elif choice == 3:
            # Fuzz normalize_string_prefix()
            prefixes = ["", "r", "R", "f", "F", "b", "B", "u", "U", "rf", "RF", "fr", "FR", "br", "BR", "rb", "RB"]
            prefix = fdp.PickValueInList(prefixes)
            content = fdp.ConsumeUnicodeNoSurrogates(128)
            test_str = f'{prefix}"{content}"'
            normalize_string_prefix(test_str)

    except (SyntaxError, ValueError, InvalidInput, AssertionError,
            AttributeError, IndexError, KeyError, RecursionError):
        pass
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
