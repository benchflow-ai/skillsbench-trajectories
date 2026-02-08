import atheris
import sys

with atheris.instrument_imports():
    import tokenize
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils.tokenutil import token_at_cursor
    from IPython.utils.openpy import source_to_unicode

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz transform_cell
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        if not src:
            return
        try:
            tm = TransformerManager()
            tm.transform_cell(src)
        except (SyntaxError, ValueError, TypeError, OverflowError, MemoryError,
                RuntimeError, UnicodeDecodeError, UnicodeEncodeError,
                IndexError, KeyError, RecursionError, tokenize.TokenError):
            pass
    elif choice == 1:
        # Fuzz check_complete
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        if not src:
            return
        try:
            tm = TransformerManager()
            tm.check_complete(src)
        except (SyntaxError, ValueError, TypeError, OverflowError, MemoryError,
                RuntimeError, UnicodeDecodeError, UnicodeEncodeError,
                IndexError, KeyError, RecursionError, tokenize.TokenError):
            pass
    elif choice == 2:
        # Fuzz token_at_cursor
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        if not src:
            return
        cursor_pos = fdp.ConsumeIntInRange(0, max(len(src), 1))
        try:
            token_at_cursor(src, cursor_pos)
        except (SyntaxError, ValueError, TypeError, IndexError,
                tokenize.TokenError):
            pass
    else:
        # Fuzz source_to_unicode
        raw = fdp.ConsumeBytes(fdp.remaining_bytes())
        if not raw:
            return
        try:
            source_to_unicode(raw)
        except (SyntaxError, ValueError, TypeError, UnicodeDecodeError,
                LookupError):
            pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
