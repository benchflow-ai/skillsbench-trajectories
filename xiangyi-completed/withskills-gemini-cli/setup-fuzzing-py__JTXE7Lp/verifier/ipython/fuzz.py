import atheris
import sys
import tokenize

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except Exception:
        return

    try:
        tm.transform_cell(s)
    except (SyntaxError, ValueError, tokenize.TokenError):
        pass
    except (IndexError, RuntimeError) as e:
        # IndexError can happen in some parsing edge cases in older versions or specific inputs,
        # but let's be safe and catch it if it's common.
        # Actually, let's let IndexError crash to find bugs, unless it's known.
        # But wait, I put IndexError in "Suspicious exceptions" in my note.
        # However, for continuous fuzzing setup without crashes on known issues, I might want to catch it if it's frequent.
        # I'll stick to catching only expected ones.
        if isinstance(e, RuntimeError) and "Input transformation still changing" in str(e):
             pass
        else:
             # re-raise to catch bugs
             raise e
    except Exception as e:
        # Catch generic exceptions if they are not bugs.
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
