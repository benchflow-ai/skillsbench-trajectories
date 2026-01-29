import atheris
import sys
import torch

with atheris.instrument_imports():
    from minisgl.kvcache.radix_manager import RadixCacheManager, RadixTreeNode

# Trigger JIT compilation once
try:
    from minisgl.kernel import fast_compare_key
    fast_compare_key(torch.tensor([1], dtype=torch.int32), torch.tensor([1], dtype=torch.int32))
except Exception:
    pass

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    device = torch.device("cpu")
    mgr = RadixCacheManager(device)
    
    ops = fdp.ConsumeIntInRange(1, 20)
    for _ in range(ops):
        op_type = fdp.ConsumeIntInRange(0, 2)
        if op_type == 0: # insert
            l = fdp.ConsumeIntInRange(1, 50)
            tokens = fdp.ConsumeIntListInRange(l, 0, 1000)
            if not tokens: continue
            t = torch.tensor(tokens, dtype=torch.int32, device=device)
            indices = torch.arange(len(tokens), dtype=torch.int32, device=device) 
            try:
                mgr.insert_prefix(t, indices)
            except Exception:
                 pass
        elif op_type == 1: # match
            l = fdp.ConsumeIntInRange(1, 50)
            tokens = fdp.ConsumeIntListInRange(l, 0, 1000)
            if not tokens: continue
            t = torch.tensor(tokens, dtype=torch.int32, device=device)
            mgr.match_prefix(t)
        elif op_type == 2: # evict
             s = fdp.ConsumeIntInRange(0, mgr.evictable_size)
             try:
                 mgr.evict(s)
             except Exception:
                 pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
