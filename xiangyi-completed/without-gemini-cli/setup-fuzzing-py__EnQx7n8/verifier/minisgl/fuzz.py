import atheris
import sys
import os

# Add the minisgl python directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "python"))

import torch
import numpy as np
from minisgl.message.utils import deserialize_type
from minisgl.message.tokenizer import TokenizeMsg, DetokenizeMsg, AbortMsg, BatchTokenizerMsg
from minisgl.core import SamplingParams

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    cls_map = {
        "TokenizeMsg": TokenizeMsg,
        "DetokenizeMsg": DetokenizeMsg,
        "AbortMsg": AbortMsg,
        "BatchTokenizerMsg": BatchTokenizerMsg,
        "SamplingParams": SamplingParams,
    }
    
    try:
        # We need a dictionary with __type__
        type_choice = fdp.PickValueInList(list(cls_map.keys()) + ["Tensor"])
        
        d = {"__type__": type_choice}
        if type_choice == "Tensor":
            d["buffer"] = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
            d["dtype"] = fdp.PickValueInList(["float32", "int32", "int64"])
        elif type_choice == "TokenizeMsg":
            d["uid"] = fdp.ConsumeInt(4)
            d["text"] = fdp.ConsumeUnicodeNoSurrogates(100)
            d["sampling_params"] = {"__type__": "SamplingParams", "temperature": fdp.ConsumeFloat()}
        # Add more fields if needed
        
        deserialize_type(cls_map, d)
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
