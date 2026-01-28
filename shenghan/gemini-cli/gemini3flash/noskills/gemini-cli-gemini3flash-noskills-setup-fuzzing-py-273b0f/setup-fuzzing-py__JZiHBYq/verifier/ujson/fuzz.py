import atheris
import sys
import ujson

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    input_str = fdp.ConsumeUnicodeNoSurrogates(4096)
    try:
        ujson.loads(input_str)
    except ValueError:
        pass
    except Exception as e:
        # ujson might throw other things? but usually ValueError for bad JSON
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
