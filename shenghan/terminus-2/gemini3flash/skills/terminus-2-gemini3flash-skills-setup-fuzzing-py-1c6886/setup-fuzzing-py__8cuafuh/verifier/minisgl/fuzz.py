import atheris
import sys
import json
from minisgl.message.frontend import decoder

with atheris.instrument_imports():
    from minisgl.message.frontend import decoder

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Try to create a dictionary from fuzzed data
        # A simple way is to try parsing as JSON if it's a string
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                decoder(d)
        except json.JSONDecodeError:
            pass
    except Exception as e:
        print(f"Unexpected exception: {type(e)}: {e}")
        raise e

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
