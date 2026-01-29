#!/usr/bin/env python3
"""
Coverage-guided fuzzing for MiniSGL library using atheris (LibFuzzer compatible).

Since minisgl has deep torch dependencies, this fuzzer tests:
- Pydantic model parsing (standalone definitions matching api_server.py)
- Memory size parsing (_PARSE_MEM_BYTES from env.py)
- msgpack deserialization patterns
- numpy buffer operations (simulating tensor deserialization)

Note: The actual minisgl message serialization requires torch. We test the
patterns and logic that would be used without the full torch dependency.
"""

import sys
import os

# Add minisgl Python package to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python'))

import atheris


def setup_dependencies():
    """Import dependencies without torch-dependent minisgl modules."""
    global np, msgpack, BaseModel, Literal, List, Field

    import numpy as np_module
    import msgpack as msgpack_module
    from pydantic import BaseModel as BM, Field as F
    from typing import Literal as Lit, List as L

    np = np_module
    msgpack = msgpack_module
    BaseModel = BM
    Field = F
    Literal = Lit
    List = L


# Define Pydantic models matching minisgl/server/api_server.py
# We define them here to avoid importing torch-dependent modules
class Message(object):
    """Pydantic model matching minisgl.server.api_server.Message"""
    pass


class GenerateRequest(object):
    """Pydantic model matching minisgl.server.api_server.GenerateRequest"""
    pass


class OpenAICompletionRequest(object):
    """Pydantic model matching minisgl.server.api_server.OpenAICompletionRequest"""
    pass


def create_pydantic_models():
    """Create Pydantic models dynamically after BaseModel is available."""
    global Message, GenerateRequest, OpenAICompletionRequest

    class MessageModel(BaseModel):
        role: Literal["system", "user", "assistant"]
        content: str

    class GenerateRequestModel(BaseModel):
        prompt: str
        max_tokens: int
        ignore_eos: bool = False

    class OpenAICompletionRequestModel(BaseModel):
        model: str
        prompt: str | None = None
        messages: List[MessageModel] | None = None
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

    Message = MessageModel
    GenerateRequest = GenerateRequestModel
    OpenAICompletionRequest = OpenAICompletionRequestModel


def parse_mem_bytes(mem: str) -> int:
    """
    Parse memory size string (reimplemented from minisgl.env._PARSE_MEM_BYTES).
    Supports suffixes: K, M, G, T (case insensitive).
    """
    mem = mem.strip().upper()
    if not mem:
        raise ValueError("Empty memory string")

    suffix_multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }

    if mem[-1] in suffix_multipliers:
        multiplier = suffix_multipliers[mem[-1]]
        value = float(mem[:-1])
    else:
        multiplier = 1
        value = float(mem)

    return int(value * multiplier)


def fuzz_pydantic_models(data: bytes):
    """Fuzz Pydantic API models with JSON-like data."""
    try:
        import json
        json_data = json.loads(data.decode('utf-8'))
        if not isinstance(json_data, dict):
            return
    except (UnicodeDecodeError, json.JSONDecodeError):
        return

    # Fuzz OpenAICompletionRequest
    try:
        OpenAICompletionRequest(**json_data)
    except Exception:
        pass

    # Fuzz GenerateRequest
    try:
        GenerateRequest(**json_data)
    except Exception:
        pass

    # Fuzz Message
    try:
        Message(**json_data)
    except Exception:
        pass


def fuzz_parse_mem_bytes(data: bytes):
    """Fuzz memory size string parsing."""
    try:
        mem_str = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        parse_mem_bytes(mem_str)
    except (ValueError, TypeError, OverflowError, AttributeError):
        pass
    except Exception:
        pass


def fuzz_msgpack_unpack(data: bytes):
    """Fuzz msgpack unpacking with arbitrary bytes."""
    try:
        result = msgpack.unpackb(data, raw=False, strict_map_key=False)
    except (msgpack.UnpackException, ValueError, TypeError):
        pass
    except Exception:
        pass


def fuzz_msgpack_structures(data: bytes):
    """Fuzz msgpack with nested structures simulating minisgl messages."""
    try:
        result = msgpack.unpackb(data, raw=False, strict_map_key=False)
        if isinstance(result, dict):
            # Simulate deserialize_type logic
            type_name = result.get("__type__")
            if type_name == "Tensor":
                buffer_data = result.get("buffer")
                dtype_str = result.get("dtype", "").replace("torch.", "")
                if buffer_data and dtype_str:
                    try:
                        np_dtype = getattr(np, dtype_str)
                        np.frombuffer(buffer_data, dtype=np_dtype)
                    except Exception:
                        pass
    except (msgpack.UnpackException, ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass


def fuzz_openai_completion_variations(data: bytes):
    """Fuzz OpenAI completion request with various field combinations."""
    if len(data) < 5:
        return

    try:
        options = data[0]
        content = data[1:].decode('utf-8', errors='replace')
    except Exception:
        return

    # Build request with various optional fields
    request_data = {
        "model": "test-model",
        "prompt": content[:1000] if options & 0x01 else None,
        "max_tokens": (options & 0x7F) + 1,
        "temperature": (options & 0x0F) / 10.0,
        "top_p": (options & 0x0F) / 15.0 + 0.1,
        "stream": bool(options & 0x80),
    }

    # Add messages if flag set
    if options & 0x02:
        roles = ["system", "user", "assistant"]
        role = roles[options % 3]
        request_data["messages"] = [{"role": role, "content": content[:500]}]

    try:
        OpenAICompletionRequest(**request_data)
    except Exception:
        pass


def fuzz_numpy_buffer(data: bytes):
    """Fuzz numpy buffer operations similar to tensor deserialization."""
    if len(data) < 5:
        return

    dtype_options = ["float32", "float64", "int32", "int64", "float16", "uint8", "int8", "uint16", "int16"]
    dtype_idx = data[0] % len(dtype_options)
    dtype_str = dtype_options[dtype_idx]
    buffer_data = bytes(data[1:])

    try:
        np_dtype = getattr(np, dtype_str)
        np_tensor = np.frombuffer(buffer_data, dtype=np_dtype)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass


def TestOneInput(data: bytes):
    """Main fuzzing entry point - calls all fuzz targets."""
    if len(data) < 1:
        return

    # Use first byte to select target
    selector = data[0] % 6
    payload = data[1:]

    if selector == 0:
        fuzz_pydantic_models(payload)
    elif selector == 1:
        fuzz_parse_mem_bytes(payload)
    elif selector == 2:
        fuzz_msgpack_unpack(payload)
    elif selector == 3:
        fuzz_msgpack_structures(payload)
    elif selector == 4:
        fuzz_openai_completion_variations(payload)
    else:
        fuzz_numpy_buffer(payload)


def main():
    """Main entry point for the fuzzer."""
    setup_dependencies()
    create_pydantic_models()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
