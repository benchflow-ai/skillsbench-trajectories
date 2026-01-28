import sys
import atheris
import torch
import numpy as np
from minisgl.message.utils import deserialize_type
from minisgl.message.frontend import UserReply, BatchFrontendMsg

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # We need a dictionary for deserialize_type
        # Fuzzing a dictionary is tricky with raw bytes, 
        # but we can try to build one or use a JSON parser if available.
        # For simplicity, let's try to fuzz the Tensor deserialization path
        # or a simple message.
        
        type_choice = fdp.ConsumeIntInRange(0, 1)
        if type_choice == 0:
            # Tensor path
            dtype_str = fdp.PickValueInList(["float32", "int32", "float16"])
            buffer = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
            d = {
                "__type__": "Tensor",
                "buffer": buffer,
                "dtype": dtype_str
            }
            deserialize_type({}, d)
        else:
            # UserReply path
            uid = fdp.ConsumeInt(4)
            output = fdp.ConsumeUnicodeNoSurrogates(1024)
            finished = fdp.ConsumeBool()
            d = {
                "__type__": "UserReply",
                "uid": uid,
                "incremental_output": output,
                "finished": finished
            }
            cls_map = {"UserReply": UserReply}
            deserialize_type(cls_map, d)
            
    except (Exception, AssertionError):
        # We expect some failures due to random data
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
