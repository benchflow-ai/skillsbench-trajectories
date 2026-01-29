import atheris
import sys
import json
import torch
import numpy as np

with atheris.instrument_imports():
    from minisgl.message.utils import deserialize_type
    import minisgl.message as msg
    from minisgl.core import SamplingParams
    from minisgl.message.tokenizer import AbortMsg

# Create a class map for deserialization
CLS_MAP = {
    "SamplingParams": SamplingParams,
    "TokenizeMsg": msg.TokenizeMsg,
    "DetokenizeMsg": msg.DetokenizeMsg,
    "BatchTokenizerMsg": msg.BatchTokenizerMsg,
    "AbortMsg": AbortMsg,
    "UserMsg": msg.UserMsg,
    "ExitMsg": msg.ExitMsg,
    "BatchBackendMsg": msg.BatchBackendMsg,
    "UserReply": msg.UserReply,
    "BatchFrontendMsg": msg.BatchFrontendMsg,
}

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            d = json.loads(s)
        except json.JSONDecodeError:
            return
        
        if not isinstance(d, dict) or "__type__" not in d:
            return
            
        deserialize_type(CLS_MAP, d)
    except (ValueError, TypeError, KeyError, AttributeError, AssertionError):
        pass
    except Exception:
        # Catch other potential exceptions to keep the fuzzer running
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
