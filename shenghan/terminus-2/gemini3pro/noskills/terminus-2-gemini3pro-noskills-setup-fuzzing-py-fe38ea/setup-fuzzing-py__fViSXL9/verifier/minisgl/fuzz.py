import atheris
import sys
import minisgl.tokenizer.tokenize as mtokenize
from minisgl.message import TokenizeMsg
import torch

# Mock tokenizer
class MockTokenizer:
    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=True):
        return ""
    def encode(self, prompt, return_tensors="pt"):
        return torch.tensor([[1, 2, 3]])

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        tm = mtokenize.TokenizeManager(MockTokenizer())
        msg = TokenizeMsg(text=s)
        tm.tokenize([msg])
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
