import sys
import atheris
import json

with atheris.instrument_imports():
    from minisgl.message.frontend import BaseFrontendMsg

def TestOneInput(data):
    try:
        s = data.decode('utf-8')
        obj = json.loads(s)
        if isinstance(obj, dict):
            BaseFrontendMsg.decoder(obj)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, KeyError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
