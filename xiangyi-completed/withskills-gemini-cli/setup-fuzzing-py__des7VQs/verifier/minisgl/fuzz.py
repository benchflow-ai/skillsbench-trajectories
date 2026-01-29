import atheris
import sys
import os

with atheris.instrument_imports():
    import torch
    from minisgl.kernel.radix import fast_compare_key

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Create two tensors from fuzzed data
        size1 = fdp.ConsumeIntInRange(0, 100)
        size2 = fdp.ConsumeIntInRange(0, 100)
        
        t1 = torch.tensor(fdp.ConsumeIntList(size1, 4), dtype=torch.int32)
        t2 = torch.tensor(fdp.ConsumeIntList(size2, 4), dtype=torch.int32)
        
        try:
            fast_compare_key(t1, t2)
        except Exception:
            # Native code might raise various exceptions or crash
            pass
            
    except Exception:
        raise

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
