import atheris
import sys
import json
# We need to ensure minisgl is in path if not installed, but usually it is handled by installation
import minisgl.message.tokenizer
from minisgl.message.tokenizer import BaseTokenizerMsg

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        json_data = json.loads(s)
        if isinstance(json_data, dict):
             BaseTokenizerMsg.decoder(json_data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, AssertionError):
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
