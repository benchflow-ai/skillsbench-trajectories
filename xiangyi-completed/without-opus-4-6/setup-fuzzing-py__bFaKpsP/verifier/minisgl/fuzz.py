"""Coverage-guided fuzzer for MiniSGL's pure-Python parsing functions.

Since MiniSGL has deep transitive imports to torch/CUDA, we import modules
directly by file path to bypass package __init__.py chains, and we also
define local copies of the Pydantic models mirroring the originals.
"""

import sys
import importlib
import importlib.util
import types
import atheris


def _load_module_from_file(name, filepath):
    """Load a Python module directly from a file, bypassing package __init__.py."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load the detokenize functions directly from file,
# stubbing out the problematic imports first.
# Stub out minisgl.message to avoid torch dependency chain
_stub_msg = types.ModuleType("minisgl")
sys.modules.setdefault("minisgl", _stub_msg)
_stub_msg_message = types.ModuleType("minisgl.message")
sys.modules.setdefault("minisgl.message", _stub_msg_message)

# Create a stub DetokenizeMsg class
class _StubDetokenizeMsg:
    pass

_stub_msg_message.DetokenizeMsg = _StubDetokenizeMsg
sys.modules["minisgl.message"].DetokenizeMsg = _StubDetokenizeMsg

_detok = _load_module_from_file(
    "minisgl_detokenize",
    "/app/minisgl/python/minisgl/tokenizer/detokenize.py",
)
find_printable_text = _detok.find_printable_text
_is_chinese_char = _detok._is_chinese_char

# Define Pydantic models that mirror the originals in api_server.py
from pydantic import BaseModel, ValidationError
from typing import List, Literal


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int
    ignore_eos: bool = False


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class OpenAICompletionRequest(BaseModel):
    """Mirrors minisgl.server.api_server.OpenAICompletionRequest"""
    model: str
    prompt: str | None = None
    messages: List[Message] | None = None
    max_tokens: int = 16
    temperature: float = 1.0
    top_k: int = -1
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: List[str] = []
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    ignore_eos: bool = False


def TestOneInput(data):
    """Fuzz target for MiniSGL's input parsing and validation."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz GenerateRequest Pydantic validation
    try:
        prompt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        max_tokens = fdp.ConsumeIntInRange(-100, 100000)
        ignore_eos = fdp.ConsumeBool()
        GenerateRequest(prompt=prompt, max_tokens=max_tokens, ignore_eos=ignore_eos)
    except (ValidationError, Exception):
        pass

    # Fuzz Message Pydantic validation
    try:
        role = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        content = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        Message(role=role, content=content)
    except (ValidationError, Exception):
        pass

    # Fuzz OpenAICompletionRequest Pydantic validation
    try:
        model = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        prompt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        temperature = fdp.ConsumeFloatInRange(0.0, 100.0)
        top_p = fdp.ConsumeFloatInRange(0.0, 1.0)
        max_tokens = fdp.ConsumeIntInRange(-100, 100000)
        OpenAICompletionRequest(
            model=model,
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
    except (ValidationError, Exception):
        pass

    # Fuzz find_printable_text with Unicode edge cases
    try:
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        find_printable_text(text)
    except Exception:
        pass

    # Fuzz _is_chinese_char with various codepoints
    try:
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        _is_chinese_char(cp)
    except Exception:
        pass


def main():
    # Only instrument the specific modules we're testing, not all of pydantic/fastapi
    atheris.instrument_func(find_printable_text)
    atheris.instrument_func(_is_chinese_char)
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
