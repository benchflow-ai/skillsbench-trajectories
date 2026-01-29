import sys
import atheris
import torch
from unittest.mock import MagicMock
from minisgl.tokenizer.tokenize import TokenizeManager
from minisgl.message import TokenizeMsg
from minisgl.core import SamplingParams

# Mock tokenizer
mock_tokenizer = MagicMock()
mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
mock_tokenizer.apply_chat_template.return_value = "mock prompt"

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        tm = TokenizeManager(mock_tokenizer)
        msg = TokenizeMsg(
            uid=0,
            text=s,
            sampling_params=SamplingParams()
        )
        tm.tokenize([msg])
    except Exception as e:
        pass

def main():
    atheris.instrument_imports(["minisgl"])
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
