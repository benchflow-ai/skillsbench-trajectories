import atheris
import sys
import json

with atheris.instrument_imports():
    from minisgl.message.utils import deserialize_type
    from minisgl.message import frontend

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        d = json.loads(s)
        if isinstance(d, dict):
            scope = frontend.__dict__
            deserialize_type(scope, d)
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()