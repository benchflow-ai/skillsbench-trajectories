import atheris
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies that might be missing or hard to install
sys.modules['transformers'] = MagicMock()
sys.modules['sgl_kernel'] = MagicMock()
sys.modules['flashinfer'] = MagicMock()
sys.modules['flashinfer.ops'] = MagicMock()
# torch might be needed, let's hope it installs. If not, we might need to mock torch too, 
# but TokenizeManager uses torch.Tensor.

import torch
from minisgl.tokenizer.tokenize import TokenizeManager
from minisgl.message.tokenizer import TokenizeMsg
from minisgl.core import SamplingParams

# Mock tokenizer instance
mock_tokenizer = MagicMock()
mock_tokenizer.apply_chat_template.return_value = "mock_prompt"
mock_tokenizer.encode.return_value = torch.tensor([1, 2, 3], dtype=torch.int32)

tm = TokenizeManager(mock_tokenizer)

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        # create dummy sampling params
        sp = SamplingParams()
        msg = TokenizeMsg(uid=1, text=s, sampling_params=sp)
        tm.tokenize([msg])
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
