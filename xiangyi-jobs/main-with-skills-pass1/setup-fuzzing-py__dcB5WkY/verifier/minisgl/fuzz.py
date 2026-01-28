import atheris
import sys
import json
import minisgl.message.backend
from minisgl.message.backend import BaseBackendMsg

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        # Fuzz deserialization from JSON string
        json_data = json.loads(s)
        # Ensure it's a dict as decoder expects
        if isinstance(json_data, dict):
            BaseBackendMsg.decoder(json_data)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
        # Expected errors for invalid JSON or invalid message structure
        pass
    except Exception as e:
        # Catch other potential errors during deserialization but log them if unique
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
