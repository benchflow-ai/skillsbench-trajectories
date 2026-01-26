import atheris
import sys
import IPython.core.inputtransformer2 as ipt2

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        lines = s.splitlines(keepends=True)
        ipt2.make_tokens_by_line(lines)
    except (SyntaxError, ValueError, IndexError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
