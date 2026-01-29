import atheris
import sys
import json

with atheris.instrument_imports():
    from minisgl.message.utils import deserialize_type
    from minisgl.message.tokenizer import (
        BatchTokenizerMsg,
        DetokenizeMsg,
        TokenizeMsg,
        AbortMsg
    )
    from minisgl.core import SamplingParams

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            msg_dict = json.loads(json_str)
        except json.JSONDecodeError:
            return

        cls_map = {
            "BatchTokenizerMsg": BatchTokenizerMsg,
            "DetokenizeMsg": DetokenizeMsg,
            "TokenizeMsg": TokenizeMsg,
            "AbortMsg": AbortMsg,
            "SamplingParams": SamplingParams
        }

        try:
            deserialize_type(cls_map, msg_dict)
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
    except Exception:
        raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
