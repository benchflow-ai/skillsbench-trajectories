import sys
import atheris
import black
from black import Mode

@atheris.instrument_func
def test_black_format_str(data):
    """Fuzz black.format_str() with various Python code inputs"""
    if len(data) < 1:
        return
    
    try:
        code = data.decode('utf-8', errors='ignore')
        black.format_str(code, mode=Mode())
    except (ValueError, TypeError, SyntaxError, black.NothingChanged):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_black_parse_ast(data):
    """Fuzz black's AST parsing"""
    if len(data) < 1:
        return
    
    try:
        code = data.decode('utf-8', errors='ignore')
        black.lib2to3_parse(code)
    except (ValueError, TypeError, SyntaxError):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_black_with_options(data):
    """Fuzz black formatting with various mode options"""
    if len(data) < 1:
        return
    
    try:
        code = data.decode('utf-8', errors='ignore')
        # Test with different mode configurations
        mode = Mode(line_length=88)
        black.format_str(code, mode=mode)
    except (ValueError, TypeError, SyntaxError, black.NothingChanged):
        pass
    except Exception:
        pass

def TestOneInput(data):
    test_black_format_str(data)
    test_black_parse_ast(data)
    test_black_with_options(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
