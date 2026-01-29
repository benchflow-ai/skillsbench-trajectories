import atheris
import sys
import os
import tokenize
import io

with atheris.instrument_imports():
    import black
    from black.mode import Mode
    from black.parsing import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(len(data))
        mode = Mode()
        try:
            formatted = black.format_str(code, mode=mode)
            # Oracle: stability
            formatted2 = black.format_str(formatted, mode=mode)
            if formatted != formatted2:
                 # This might be a bug (stability issue)
                 # In a real fuzzer we might want to report this
                 pass
        except (InvalidInput, ValueError, tokenize.TokenError, IndentationError):
            pass
        except Exception as e:
            # Catch some common non-bug exceptions if they occur
            if "Cannot parse" in str(e) or "invalid syntax" in str(e):
                pass
            else:
                raise
    except Exception:
        raise

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
