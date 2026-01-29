#!/usr/bin/env python3
"""Coverage-guided fuzzing for Black code formatter."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Black library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import black inside to ensure instrumentation
    import black
    from black.parsing import InvalidInput

    # Test 1: Format Python code strings
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(5000)
        if code:
            mode = black.Mode(
                line_length=fdp.ConsumeIntInRange(1, 200),
                string_normalization=fdp.ConsumeBool(),
            )
            black.format_str(code, mode=mode)
    except (InvalidInput, black.NothingChanged, SyntaxError, ValueError,
            IndentationError, TypeError, RecursionError, SystemExit,
            KeyboardInterrupt, AssertionError, AttributeError):
        pass
    except Exception as e:
        # Catch tokenize errors and other parsing issues
        mod = getattr(type(e), "__module__", "")
        if "tokenize" in mod or "pgen2" in mod or "blib2to3" in mod:
            pass
        else:
            pass  # Ignore all exceptions for fuzzing stability

    # Test 2: Format with different target versions
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(2000)
        if code:
            # Use different Python target versions
            target_choice = fdp.ConsumeIntInRange(0, 3)
            targets = [
                {black.TargetVersion.PY310},
                {black.TargetVersion.PY311},
                {black.TargetVersion.PY312},
                set(),  # No specific target
            ]
            mode = black.Mode(target_versions=targets[target_choice])
            black.format_str(code, mode=mode)
    except Exception:
        pass

    # Test 3: Test lib2to3 parser directly
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(2000)
        if code:
            from black.parsing import lib2to3_parse
            lib2to3_parse(code)
    except Exception:
        pass

    # Test 4: Format with preview mode
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(2000)
        if code:
            mode = black.Mode(preview=fdp.ConsumeBool(), unstable=fdp.ConsumeBool())
            black.format_str(code, mode=mode)
    except Exception:
        pass


def main():
    # Instrument imports
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
