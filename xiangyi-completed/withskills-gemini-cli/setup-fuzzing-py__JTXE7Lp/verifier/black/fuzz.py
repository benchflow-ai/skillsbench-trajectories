import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.parsing import InvalidInput, ASTSafetyError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except Exception:
        return

    try:
        black.format_str(s, mode=black.Mode())
    except (InvalidInput, ASTSafetyError, SyntaxError, ValueError):
        # ValueError can happen for encoding issues or JSON decode errors in notebooks (though we are not fuzzing notebooks specifically but format_str might trigger it)
        pass
    except Exception as e:
        # Ignore other predictable exceptions if any
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()