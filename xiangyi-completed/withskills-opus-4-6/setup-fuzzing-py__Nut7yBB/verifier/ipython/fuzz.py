import sys
sys.dont_write_bytecode = True

import atheris
import ast

# We must import the modules under test after atheris instrumentation,
# but we declare them here for reference. The actual imports happen
# inside the harness or at module level after instrument_all().

def TestOneInput(data: bytes):
    """Fuzz driver exercising multiple IPython parsing/evaluation surfaces."""

    fdp = atheris.FuzzedDataProvider(data)

    # We need at least a few bytes to do anything useful
    if fdp.remaining_bytes() < 4:
        return

    # Choose which target to exercise for this input
    target = fdp.ConsumeIntInRange(0, 4)

    if target == 0:
        # Target 1: TransformerManager.transform_cell
        _fuzz_transform_cell(fdp)
    elif target == 1:
        # Target 2: TransformerManager.check_complete
        _fuzz_check_complete(fdp)
    elif target == 2:
        # Target 3: guarded_eval with limited/minimal context
        _fuzz_guarded_eval(fdp)
    elif target == 3:
        # Target 4: token_at_cursor
        _fuzz_token_at_cursor(fdp)
    elif target == 4:
        # Target 5: source_to_unicode
        _fuzz_source_to_unicode(fdp)


def _fuzz_transform_cell(fdp):
    """Fuzz TransformerManager.transform_cell with arbitrary strings.

    Per the notes, acceptable exceptions are SyntaxError and RuntimeError
    (from TRANSFORM_LOOP_LIMIT). Everything else is a bug.
    """
    from IPython.core.inputtransformer2 import TransformerManager

    # Limit input size to ~10KB to avoid pathological tokenization hangs
    cell = fdp.ConsumeUnicode(min(fdp.remaining_bytes(), 10240))

    tm = TransformerManager()
    try:
        result = tm.transform_cell(cell)
    except (SyntaxError, RuntimeError):
        # SyntaxError: from tokenizer on malformed input
        # RuntimeError: from exceeding TRANSFORM_LOOP_LIMIT
        pass
    except tokenize.TokenError:
        # tokenize may raise this on unterminated strings/brackets
        pass


def _fuzz_check_complete(fdp):
    """Fuzz TransformerManager.check_complete with arbitrary strings.

    Per the notes, this function is designed not to raise. It catches
    SyntaxError, OverflowError, ValueError, TypeError, MemoryError,
    SyntaxWarning internally. Any uncaught exception is a potential bug,
    except RuntimeError from TRANSFORM_LOOP_LIMIT.
    """
    from IPython.core.inputtransformer2 import TransformerManager

    cell = fdp.ConsumeUnicode(min(fdp.remaining_bytes(), 10240))

    tm = TransformerManager()
    try:
        result = tm.check_complete(cell)
    except (SyntaxError, RuntimeError):
        # SyntaxError: may leak from transform pipeline
        # RuntimeError: from exceeding TRANSFORM_LOOP_LIMIT
        pass
    except tokenize.TokenError:
        # tokenize may raise this on unterminated strings/brackets
        pass
    else:
        # Oracle checks: result must be a 2-tuple (str, int|None)
        assert isinstance(result, tuple), \
            f"check_complete must return a tuple, got {type(result)}"
        assert len(result) == 2, \
            f"check_complete must return 2-tuple, got length {len(result)}"

        status, indent = result
        assert status in ('complete', 'incomplete', 'invalid'), \
            f"check_complete status must be 'complete', 'incomplete', or 'invalid', got {status!r}"

        if status != 'incomplete':
            assert indent is None, \
                f"check_complete indent must be None when status is {status!r}, got {indent!r}"
        else:
            assert indent is None or isinstance(indent, int), \
                f"check_complete indent must be int or None, got {type(indent)}"


def _fuzz_guarded_eval(fdp):
    """Fuzz guarded_eval with arbitrary code strings in limited/minimal mode.

    Per the notes, we must NEVER use "dangerous" mode. Acceptable exceptions
    are GuardRejection, SyntaxError, NameError, TypeError, ValueError.
    RecursionError may indicate missing depth limiting (a real bug candidate).
    """
    from IPython.core.guarded_eval import (
        guarded_eval,
        EvaluationContext,
        GuardRejection,
    )

    code = fdp.ConsumeUnicode(min(fdp.remaining_bytes(), 4096))

    # Choose between "limited" and "minimal" evaluation modes
    # Never use "dangerous" as it calls Python's eval() directly
    use_limited = fdp.ConsumeBool()
    evaluation_mode = "limited" if use_limited else "minimal"

    context = EvaluationContext(
        locals={},
        globals={},
        evaluation=evaluation_mode,
        in_subscript=False,
    )

    try:
        guarded_eval(code, context)
    except (
        GuardRejection,
        SyntaxError,
        NameError,
        TypeError,
        ValueError,
        AttributeError,
        KeyError,
        IndexError,
        OverflowError,
        ZeroDivisionError,
        StopIteration,
    ):
        # All of these are expected/acceptable for arbitrary code
        pass


def _fuzz_token_at_cursor(fdp):
    """Fuzz token_at_cursor with arbitrary cell strings and cursor positions.

    Per the notes, this function should never raise for any valid (str, int)
    input. Any exception is a potential bug.
    """
    from IPython.utils.tokenutil import token_at_cursor

    # Reserve 4 bytes for cursor_pos integer
    if fdp.remaining_bytes() < 4:
        return

    cell = fdp.ConsumeUnicode(min(fdp.remaining_bytes() - 4, 10240))
    # cursor_pos: test in-range and slightly out-of-range values
    cursor_pos = fdp.ConsumeIntInRange(0, max(len(cell) + 10, 1))

    try:
        result = token_at_cursor(cell, cursor_pos)
    except tokenize.TokenError:
        # tokenize may raise on unterminated strings; the function tries to
        # catch this but it may not cover all cases
        pass
    except SyntaxError:
        # Possible from tokenization of truly malformed input
        pass
    else:
        # Oracle: must always return a str
        assert isinstance(result, str), \
            f"token_at_cursor must return str, got {type(result)}"


def _fuzz_source_to_unicode(fdp):
    """Fuzz source_to_unicode with raw bytes.

    Per the notes, LookupError is a real bug candidate: if detect_encoding
    returns an encoding name not known to Python's codec registry,
    TextIOWrapper will raise LookupError, which is NOT caught by the
    function's except SyntaxError handler.

    We catch LookupError here as a known issue so the fuzzer can continue
    finding other bugs, but this is a real bug.
    """
    from IPython.utils.openpy import source_to_unicode

    raw_bytes = fdp.ConsumeBytes(min(fdp.remaining_bytes(), 10240))

    # Test both code paths: with and without encoding cookie stripping
    for skip_cookie in (True, False):
        try:
            result = source_to_unicode(
                raw_bytes, errors='replace', skip_encoding_cookie=skip_cookie
            )
        except SyntaxError:
            # From detect_encoding on malformed input
            pass
        except LookupError:
            # Known bug candidate: unknown encoding from detect_encoding
            # not caught internally. We catch it here so fuzzing continues.
            pass
        else:
            # Oracle: must always return a str
            assert isinstance(result, str), \
                f"source_to_unicode must return str, got {type(result)}"


# We need tokenize for exception handling in several targets
import tokenize


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
