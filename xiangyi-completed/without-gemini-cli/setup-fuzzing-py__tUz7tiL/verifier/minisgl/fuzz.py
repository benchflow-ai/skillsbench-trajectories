import atheris
import sys

with atheris.instrument_imports():
    from minisgl.core import SamplingParams
    # Add more imports as needed

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz SamplingParams
        temp = fdp.ConsumeFloat()
        top_k = fdp.ConsumeInt(32)
        top_p = fdp.ConsumeFloat()
        ignore_eos = fdp.ConsumeBool()
        max_tokens = fdp.ConsumeInt(32)
        
        params = SamplingParams(
            temperature=temp,
            top_k=top_k,
            top_p=top_p,
            ignore_eos=ignore_eos,
            max_tokens=max_tokens
        )
        
        _ = params.is_greedy
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
