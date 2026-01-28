import atheris
import sys
import torch

with atheris.instrument_imports():
    from minisgl.core import SamplingParams

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        temp = fdp.ConsumeFloat()
        top_k = fdp.ConsumeInt(1024)
        top_p = fdp.ConsumeFloat()
        ignore_eos = fdp.ConsumeBool()
        max_tokens = fdp.ConsumeInt(1024)
        
        params = SamplingParams(
            temperature=temp,
            top_k=top_k,
            top_p=top_p,
            ignore_eos=ignore_eos,
            max_tokens=max_tokens
        )
        _ = params.is_greedy
    except Exception as e:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
