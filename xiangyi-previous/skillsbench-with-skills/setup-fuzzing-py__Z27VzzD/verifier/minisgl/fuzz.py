import atheris
import sys
import json
with atheris.instrument_imports():
    from minisgl.message.tokenizer import decoder

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        d = json.loads(s)
        if isinstance(d, dict):
            decoder(d)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
