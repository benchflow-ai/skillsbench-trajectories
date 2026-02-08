import sys

sys.dont_write_bytecode = True

import atheris
import json

with atheris.instrument_imports():
    from black import Mode, format_str, decode_bytes, format_ipynb_string
    from black.parsing import lib2to3_parse
    from black.report import NothingChanged
    from black.parsing import InvalidInput
    from black.strings import normalize_string_quotes
    from blib2to3.pgen2.tokenize import TokenError
    import tokenize as _std_tokenize


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Use a selector byte to choose which target to fuzz
    target = fdp.ConsumeIntInRange(0, 4)

    if target == 0:
        # Target: format_str
        # The primary public API of Black. Accepts a Python source string and a Mode.
        src = fdp.ConsumeUnicode(fdp.remaining_bytes())
        mode = Mode()
        try:
            format_str(src, mode=mode)
        except (
            InvalidInput,
            NothingChanged,
            IndentationError,
            TokenError,
            _std_tokenize.TokenError,
            SyntaxError,
        ):
            pass

    elif target == 1:
        # Target: lib2to3_parse
        # The core parser that tokenizes and parses Python source into a CST.
        # Uses a native pytokens extension -- crashes here are especially valuable.
        src = fdp.ConsumeUnicode(fdp.remaining_bytes())
        try:
            lib2to3_parse(src)
        except InvalidInput:
            pass

    elif target == 2:
        # Target: decode_bytes
        # Accepts raw bytes, detects encoding and newline style, returns decoded str.
        raw_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())
        mode = Mode()
        try:
            decode_bytes(raw_bytes, mode)
        except (
            SyntaxError,       # from tokenize.detect_encoding on bad encoding cookie
            UnicodeDecodeError, # from decoding with detected encoding
            LookupError,       # unknown encoding name
        ):
            pass

    elif target == 3:
        # Target: normalize_string_quotes
        # Operates on a single string literal token. Uses regex-based processing
        # to swap quote characters while maintaining correct escaping.
        # Generate a plausible string literal for deeper coverage.
        prefix_chars = "fFbBrRuUtT"
        prefix = ""
        num_prefix = fdp.ConsumeIntInRange(0, 3)
        for _ in range(num_prefix):
            idx = fdp.ConsumeIntInRange(0, len(prefix_chars) - 1)
            prefix += prefix_chars[idx]

        use_triple = fdp.ConsumeBool()
        use_double = fdp.ConsumeBool()

        if use_triple:
            quote = '"""' if use_double else "'''"
        else:
            quote = '"' if use_double else "'"

        body = fdp.ConsumeUnicode(fdp.remaining_bytes())
        # Remove any occurrences of the closing quote from the body to form
        # a syntactically plausible string literal
        body = body.replace(quote, "")

        s = prefix + quote + body + quote
        try:
            normalize_string_quotes(s)
        except (
            AssertionError,   # from assert_is_leaf_string on malformed input
            ValueError,       # from malformed string literal
        ):
            pass

    elif target == 4:
        # Target: format_ipynb_string
        # Accepts a JSON string representing a Jupyter notebook.
        # Construct a minimal notebook structure with fuzzed cell source
        # for better coverage of deep code paths.
        use_structured = fdp.ConsumeBool()
        if use_structured:
            # Build a minimal notebook JSON with fuzzed cell content
            cell_source = fdp.ConsumeUnicode(fdp.remaining_bytes())
            notebook = {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": [cell_source],
                        "metadata": {},
                        "outputs": [],
                    }
                ],
                "metadata": {
                    "language_info": {"name": "python"},
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    },
                },
                "nbformat": 4,
                "nbformat_minor": 4,
            }
            src = json.dumps(notebook)
        else:
            # Feed raw fuzzed string to exercise JSON parsing error paths
            src = fdp.ConsumeUnicode(fdp.remaining_bytes())

        mode = Mode(is_ipynb=True)
        try:
            format_ipynb_string(src, fast=False, mode=mode)
        except (
            NothingChanged,
            json.JSONDecodeError,
            KeyError,           # missing "cells" key
            InvalidInput,       # from format_str on unparseable Python
            TypeError,          # unexpected types in notebook structure
            ValueError,         # various value errors from JSON or formatting
            IndentationError,
            TokenError,
            _std_tokenize.TokenError, # from stdlib tokenize via tokenize_rt
            SyntaxError,
            ModuleNotFoundError, # IPython may not be installed
            AttributeError,     # JSON decodes to non-dict (e.g. int)
            AssertionError,     # from put_trailing_semicolon_back
        ):
            pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
