#!/usr/bin/python3
"""Coverage-guided fuzz driver for IPython.

Targets:
  1. TransformerManager.transform_cell() - Input transformation pipeline
  2. TransformerManager.check_complete()  - Code completeness checking
  3. guarded_eval()                       - Guarded expression evaluation
  4. token_at_cursor()                    - Token introspection
  5. split_user_input()                   - Input line splitting
"""
import atheris
import sys
import tokenize

# Only instrument the specific modules we're fuzzing, not all transitive deps
with atheris.instrument_imports(include=[
    "IPython.core.inputtransformer2",
    "IPython.core.guarded_eval",
    "IPython.utils.tokenutil",
    "IPython.core.splitinput",
]):
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.guarded_eval import guarded_eval, EvaluationContext, GuardRejection
    from IPython.utils.tokenutil import token_at_cursor
    from IPython.core.splitinput import split_user_input

# Reusable TransformerManager instance (stateless across calls)
_tm = TransformerManager()


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    if fdp.remaining_bytes() < 2:
        return
    target = fdp.ConsumeIntInRange(0, 4)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if target == 0:
        # Target 1: transform_cell
        try:
            _tm.transform_cell(s)
        except (SyntaxError, ValueError, RuntimeError, tokenize.TokenError,
                TypeError, OverflowError, MemoryError, IndexError):
            pass

    elif target == 1:
        # Target 2: check_complete
        try:
            status, indent = _tm.check_complete(s)
        except (SyntaxError, ValueError, RuntimeError, tokenize.TokenError,
                TypeError, OverflowError, MemoryError, IndexError):
            pass

    elif target == 2:
        # Target 3: guarded_eval
        context = EvaluationContext(
            locals={"x": [1, 2, 3], "d": {"a": 1}, "s": "hello", "n": 42},
            globals={},
            evaluation="limited",
        )
        try:
            guarded_eval(s, context)
        except (GuardRejection, SyntaxError, ValueError, NameError,
                TypeError, KeyError, IndexError, AttributeError,
                ZeroDivisionError, OverflowError, RuntimeError,
                RecursionError, MemoryError, StopIteration,
                UnicodeDecodeError, UnicodeEncodeError):
            pass

    elif target == 3:
        # Target 4: token_at_cursor
        if not s:
            return
        cursor_pos = fdp.ConsumeIntInRange(0, len(s))
        try:
            token_at_cursor(s, cursor_pos)
        except (tokenize.TokenError, SyntaxError, ValueError, IndexError,
                TypeError, OverflowError):
            pass

    elif target == 4:
        # Target 5: split_user_input
        try:
            split_user_input(s)
        except (ValueError, AttributeError, TypeError, IndexError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
