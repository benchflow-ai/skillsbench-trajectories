import atheris
import sys
import json

with atheris.instrument_imports():
    from minisgl.message.utils import deserialize_type
    from minisgl.message.tokenizer import TokenizeMsg, DetokenizeMsg, BatchTokenizerMsg, AbortMsg
    from minisgl.message.frontend import UserReply, BatchFrontendMsg
    from minisgl.message.backend import UserMsg, BatchBackendMsg, ExitMsg
    from minisgl.core import SamplingParams

# Create a class map for deserialization
CLS_MAP = {
    "TokenizeMsg": TokenizeMsg,
    "DetokenizeMsg": DetokenizeMsg,
    "BatchTokenizerMsg": BatchTokenizerMsg,
    "AbortMsg": AbortMsg,
    "UserReply": UserReply,
    "BatchFrontendMsg": BatchFrontendMsg,
    "UserMsg": UserMsg,
    "BatchBackendMsg": BatchBackendMsg,
    "ExitMsg": ExitMsg,
    "SamplingParams": SamplingParams,
}

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz deserialize_type with a random JSON-like dictionary
        # We'll try to construct a dictionary that might hit deserialize_type
        json_str = fdp.ConsumeUnicodeNoSurrogates(1024)
        d = json.loads(json_str)
        if isinstance(d, dict) and "__type__" in d:
            deserialize_type(CLS_MAP, d)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError, AssertionError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
