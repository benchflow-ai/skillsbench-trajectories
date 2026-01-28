import sys
import atheris
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.inputtransformer2 import TransformerManager

@atheris.instrument_func
def test_ipython_run_cell(data):
    """Fuzz IPython cell execution"""
    if len(data) < 1:
        return
    
    try:
        shell = InteractiveShell.instance()
        code = data.decode('utf-8', errors='ignore')
        shell.run_cell(code, silent=True)
    except (ValueError, TypeError, SyntaxError, RuntimeError):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_ipython_input_transform(data):
    """Fuzz IPython input transformation"""
    if len(data) < 1:
        return
    
    try:
        tm = TransformerManager()
        code = data.decode('utf-8', errors='ignore')
        tm.transform_cell(code)
    except (ValueError, TypeError, SyntaxError):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_ipython_prefilter(data):
    """Fuzz IPython prefilter"""
    if len(data) < 1:
        return
    
    try:
        shell = InteractiveShell.instance()
        line = data.decode('utf-8', errors='ignore')
        shell.prefilter_manager.prefilter_line(line)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass

def TestOneInput(data):
    test_ipython_run_cell(data)
    test_ipython_input_transform(data)
    test_ipython_prefilter(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
