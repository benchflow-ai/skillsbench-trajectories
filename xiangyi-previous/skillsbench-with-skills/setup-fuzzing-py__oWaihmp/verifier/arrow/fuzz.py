import sys
import atheris
import arrow
from datetime import datetime

@atheris.instrument_func
def test_arrow_parsing(data):
    """Fuzz arrow.get() with various inputs"""
    if len(data) < 1:
        return
    
    # Test string parsing
    try:
        arrow.get(data.decode('utf-8', errors='ignore'))
    except (ValueError, TypeError, AttributeError, arrow.parser.ParserError):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_arrow_formatting(data):
    """Fuzz arrow formatting with various format strings"""
    if len(data) < 1:
        return
    
    try:
        arr = arrow.now()
        fmt = data.decode('utf-8', errors='ignore')
        arr.strftime(fmt)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_arrow_shift(data):
    """Fuzz arrow shift operations"""
    if len(data) < 4:
        return
    
    try:
        arr = arrow.now()
        shift_amount = int.from_bytes(data[:4], byteorder='little', signed=True)
        arr.shift(days=shift_amount)
    except (ValueError, TypeError, OverflowError):
        pass
    except Exception:
        pass

def TestOneInput(data):
    test_arrow_parsing(data)
    test_arrow_formatting(data)
    test_arrow_shift(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
