#!/usr/bin/env python3
"""
Coverage-guided fuzzing driver for the IPython library.
Uses atheris for LibFuzzer-style fuzzing.
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for IPython library."""
    # Import inside function to avoid issues during atheris setup
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input, LineInfo
    from IPython.utils._process_common import arg_split

    # Convert bytes to string for testing
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not text or len(text) > 50000:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: TransformerManager.transform_cell()
    try:
        tm = TransformerManager()
        tm.transform_cell(text)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass
    except Exception:
        pass

    # Test 2: TransformerManager.check_complete()
    try:
        tm = TransformerManager()
        tm.check_complete(text)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: split_user_input()
    try:
        split_user_input(text)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass

    # Test 4: LineInfo parsing
    try:
        li = LineInfo(text)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass

    # Test 5: arg_split() with posix mode
    try:
        arg_split(text, posix=True, strict=True)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 6: arg_split() with non-posix mode
    try:
        arg_split(text, posix=False, strict=True)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 7: arg_split() with strict=False
    try:
        arg_split(text, posix=True, strict=False)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 8: Test magic command transformations with various escape sequences
    escape_prefixes = ["%", "%%", "!", "!!", "?", "??", ",", ";", "/"]
    if len(data) > 2:
        prefix_idx = data[0] % len(escape_prefixes)
        escaped_text = escape_prefixes[prefix_idx] + text[:100]
        try:
            tm = TransformerManager()
            tm.transform_cell(escaped_text)
        except (ValueError, TypeError, SyntaxError, RecursionError):
            pass
        except Exception:
            pass

    # Test 9: Test multiline input with continuations
    if "\\" in text or "\n" in text:
        try:
            tm = TransformerManager()
            tm.transform_cell(text)
        except (ValueError, TypeError, SyntaxError, RecursionError):
            pass
        except Exception:
            pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
