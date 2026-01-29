import atheris
import sys
import ujson
import json

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        # Fuzz ujson.loads
        obj = ujson.loads(data)
        
        # If loads succeeded, try dumps
        _ = ujson.dumps(obj)
    except (ValueError, OverflowError, TypeError):
        pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
