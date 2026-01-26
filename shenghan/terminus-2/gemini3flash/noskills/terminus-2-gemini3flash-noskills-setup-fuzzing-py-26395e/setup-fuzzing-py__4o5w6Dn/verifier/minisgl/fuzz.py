import atheris
import sys
import json

with atheris.instrument_imports():
    from minisgl.message.tokenizer import decoder

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                decoder(d)
        except json.JSONDecodeError:
            pass
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
