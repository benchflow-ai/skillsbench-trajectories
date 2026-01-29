import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

# Initialize outside to avoid overhead
tm = TransformerManager()

def TestOneInput(data):
    try:
        s = data.decode('utf-8')
        tm.transform_cell(s)
    except (UnicodeDecodeError, SyntaxError, ValueError):
        pass
    except Exception:
        # Catch all for now as IPython might raise various things
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
