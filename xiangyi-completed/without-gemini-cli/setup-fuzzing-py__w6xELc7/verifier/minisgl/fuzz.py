import sys
import atheris
import argparse
# Import heavy dependencies before instrumentation to avoid instrumenting them
import torch
import transformers

atheris.instrument_all()

from minisgl.server.args import parse_args

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    # Generate random list of args
    args = []
    num_args = fdp.ConsumeIntInRange(0, 10)
    for _ in range(num_args):
        args.append(fdp.ConsumeString(fdp.ConsumeIntInRange(0, 20)))
    
    try:
        parse_args(args)
    except SystemExit:
        pass
    except Exception:
        # Might fail due to transformers not finding model, etc.
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()