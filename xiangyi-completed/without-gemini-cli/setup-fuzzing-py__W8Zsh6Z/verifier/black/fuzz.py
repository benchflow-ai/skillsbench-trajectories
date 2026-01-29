import atheris
import sys
with atheris.instrument_imports():
    import black

def TestOneInput(data):
    try:
        s = data.decode("utf-8", errors="ignore")
        black.format_str(s, mode=black.Mode())
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
