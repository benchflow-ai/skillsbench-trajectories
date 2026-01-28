import atheris
import sys
import torch
from minisgl.core import Req, SamplingParams
from minisgl.kvcache import BaseCacheHandle

# Mock BaseCacheHandle as it is an abstract base class or requires setup
class MockCacheHandle(BaseCacheHandle):
    pass

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Construct inputs
        input_len = fdp.ConsumeIntInRange(1, 100)
        input_ids = torch.tensor(fdp.ConsumeIntListInRange(input_len, 0, 1000), dtype=torch.int32)
        table_idx = fdp.ConsumeInt(4)
        cached_len = fdp.ConsumeIntInRange(0, input_len - 1)
        output_len = fdp.ConsumeIntInRange(1, 100)
        uid = fdp.ConsumeInt(4)
        
        sp = SamplingParams(
            temperature=fdp.ConsumeFloat(),
            top_k=fdp.ConsumeInt(4),
            top_p=fdp.ConsumeFloat(),
            ignore_eos=fdp.ConsumeBool(),
            max_tokens=fdp.ConsumeIntInRange(1, 1024)
        )
        
        req = Req(
            input_ids=input_ids,
            table_idx=table_idx,
            cached_len=cached_len,
            output_len=output_len,
            uid=uid,
            sampling_params=sp,
            cache_handle=MockCacheHandle()
        )
        
        # Call methods
        req.remain_len
        req.extend_len
        if req.can_decode():
            req.complete_one()
            
    except (AssertionError, ValueError, RuntimeError):
        pass
    except Exception:
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
