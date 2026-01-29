import atheris
import sys
with atheris.instrument_imports():
    import torch
    from minisgl.kernel.radix import fast_compare_key

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Create two tensors
        size1 = fdp.ConsumeIntInRange(0, 100)
        size2 = fdp.ConsumeIntInRange(0, 100)
        t1 = torch.tensor(fdp.ConsumeIntListInRange(size1, 0, 1000), dtype=torch.int32)
        t2 = torch.tensor(fdp.ConsumeIntListInRange(size2, 0, 1000), dtype=torch.int32)
        fast_compare_key(t1, t2)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
