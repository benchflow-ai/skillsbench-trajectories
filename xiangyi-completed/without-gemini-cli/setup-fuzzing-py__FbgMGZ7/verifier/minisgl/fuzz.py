import sys
import atheris
import json
import torch
# We assume torch is installed.
# We need to import the target module.
# Since we are installing the package, it should be importable.
from minisgl.message.frontend import BaseFrontendMsg

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        json_obj = json.loads(s)
        # Check if it's a dict before passing, as decoder expects a dict usually
        if isinstance(json_obj, dict):
            BaseFrontendMsg.decoder(json_obj)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError, AssertionError):
        pass
    except Exception as e:
        # Catch generic exceptions that might rise from deserialization (e.g. torch errors)
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
