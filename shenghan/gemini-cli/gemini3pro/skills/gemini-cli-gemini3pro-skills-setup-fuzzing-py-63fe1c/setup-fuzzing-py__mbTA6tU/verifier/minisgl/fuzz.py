import atheris
import sys
import torch

# Mock fast_compare_key
def mock_fast_compare_key(x: torch.Tensor, y: torch.Tensor) -> int:
    l = min(x.size(0), y.size(0))
    if l == 0:
        return 0
    
    match = 0
    for i in range(l):
        if x[i] == y[i]:
            match += 1
        else:
            break
    return match

# Instrument minisgl before importing it
with atheris.instrument_imports(include=["minisgl"]):
    import minisgl.kernel.radix
    from minisgl.kvcache.radix_manager import RadixCacheManager, RadixTreeNode
    import minisgl.kernel

# Monkey patch after import
minisgl.kernel.fast_compare_key = mock_fast_compare_key
minisgl.kernel.radix.fast_compare_key = mock_fast_compare_key
minisgl.kernel.radix._load_radix_module = lambda: None

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    device = torch.device('cpu')
    manager = RadixCacheManager(device)
    
    num_ops = fdp.ConsumeIntInRange(1, 20)
    
    for _ in range(num_ops):
        op = fdp.ConsumeIntInRange(0, 2)
        
        if op == 0: # match_prefix
            length = fdp.ConsumeIntInRange(1, 10)
            tokens = torch.tensor(fdp.ConsumeIntListInRange(length, 0, 100), dtype=torch.int32, device=device)
            if len(tokens) == 0: continue
            manager.match_prefix(tokens)
            
        elif op == 1: # insert_prefix
            length = fdp.ConsumeIntInRange(1, 10)
            tokens = torch.tensor(fdp.ConsumeIntListInRange(length, 0, 100), dtype=torch.int32, device=device)
            if len(tokens) == 0: continue
            indices = torch.arange(len(tokens), dtype=torch.int32, device=device)
            manager.insert_prefix(tokens, indices)
            
        elif op == 2: # evict
            size = fdp.ConsumeIntInRange(0, 5)
            try:
                manager.evict(size)
            except AssertionError:
                pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()