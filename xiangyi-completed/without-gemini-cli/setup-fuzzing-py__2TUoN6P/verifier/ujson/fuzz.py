import sys
import atheris
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz input as a string or bytes
        # ujson accepts both
        if fdp.ConsumeBool():
            input_data = fdp.ConsumeUnicode(sys.maxsize)
        else:
            input_data = fdp.ConsumeBytes(sys.maxsize)
            
        ujson.loads(input_data)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError):
        # Expected parsing exceptions
        pass
    except Exception as e:
        # Unexpected crashes
        raise e

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
