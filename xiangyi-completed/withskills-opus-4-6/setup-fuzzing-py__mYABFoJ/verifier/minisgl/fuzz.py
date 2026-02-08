#!/usr/bin/python3
"""Fuzz driver for minisgl library targeting deserialization, message decoding,
memory parsing, and text processing functions."""

import atheris
import sys
import importlib.util
import os

# Import heavy C extensions BEFORE instrumentation (no benefit from instrumenting C code)
import numpy as np
import torch
import msgpack

# Direct-load specific modules to avoid __init__.py transitive import chains
# that pull in zmq, transformers, etc.
_BASE = os.path.join(os.path.dirname(__file__), "python", "minisgl")


def _load_module(name, filepath):
    """Load a Python module directly from file path."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load only the modules we need, bypassing __init__.py
_core_mod = _load_module("minisgl.core", os.path.join(_BASE, "core.py"))
SamplingParams = _core_mod.SamplingParams

_msg_utils_mod = _load_module("minisgl.message.utils", os.path.join(_BASE, "message", "utils.py"))
deserialize_type = _msg_utils_mod.deserialize_type
_deserialize_any = _msg_utils_mod._deserialize_any

# For env module
_env_mod = _load_module("minisgl.env", os.path.join(_BASE, "env.py"))
_PARSE_MEM_BYTES = _env_mod._PARSE_MEM_BYTES

# For detokenize - load directly to skip tokenizer/__init__.py
_detok_mod = _load_module(
    "minisgl.tokenizer.detokenize",
    os.path.join(_BASE, "tokenizer", "detokenize.py"),
)
find_printable_text = _detok_mod.find_printable_text
_is_chinese_char = _detok_mod._is_chinese_char

# Instrument the loaded modules
atheris.instrument_func(deserialize_type)
atheris.instrument_func(_deserialize_any)
atheris.instrument_func(_msg_utils_mod._serialize_any)
atheris.instrument_func(_msg_utils_mod.serialize_type)
atheris.instrument_func(_PARSE_MEM_BYTES)
atheris.instrument_func(find_printable_text)
atheris.instrument_func(_is_chinese_char)

# Pre-build cls_map for deserialize_type fuzzing
CLS_MAP = {
    "SamplingParams": SamplingParams,
}


def fuzz_deserialize_type(fdp):
    """Fuzz deserialize_type with structured dict input."""
    choice = fdp.ConsumeIntInRange(0, 2)

    if choice == 0:
        # Fuzz Tensor deserialization path
        buffer = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))
        dtype_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 30))
        data = {
            "__type__": "Tensor",
            "buffer": buffer,
            "dtype": dtype_str,
        }
        try:
            deserialize_type({}, data)
        except (KeyError, TypeError, ValueError, AttributeError,
                AssertionError, OverflowError, RuntimeError):
            pass
    elif choice == 1:
        # Fuzz SamplingParams deserialization
        data = {
            "__type__": "SamplingParams",
            "temperature": fdp.ConsumeRegularFloat(),
            "top_k": fdp.ConsumeIntInRange(-1000, 1000),
            "top_p": fdp.ConsumeRegularFloat(),
            "ignore_eos": fdp.ConsumeBool(),
            "max_tokens": fdp.ConsumeIntInRange(-1000, 100000),
        }
        try:
            deserialize_type(CLS_MAP, data)
        except (KeyError, TypeError, ValueError, AttributeError,
                AssertionError, OverflowError):
            pass
    else:
        # Fuzz with arbitrary type name and fields
        type_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
        data = {"__type__": type_name}
        n_fields = fdp.ConsumeIntInRange(0, 5)
        for _ in range(n_fields):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 20))
            val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            data[key] = val
        try:
            deserialize_type(CLS_MAP, data)
        except (KeyError, TypeError, ValueError, AttributeError,
                AssertionError, OverflowError):
            pass


def fuzz_msgpack_deserialize(fdp):
    """Fuzz raw bytes through msgpack.unpackb -> deserialize_type."""
    raw_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())
    try:
        unpacked = msgpack.unpackb(raw_bytes, raw=False)
        if isinstance(unpacked, dict) and "__type__" in unpacked:
            deserialize_type(CLS_MAP, unpacked)
    except (msgpack.exceptions.UnpackValueError, msgpack.exceptions.ExtraData,
            KeyError, TypeError, ValueError, AttributeError,
            AssertionError, OverflowError, RuntimeError,
            UnicodeDecodeError, RecursionError):
        pass


def fuzz_parse_mem_bytes(fdp):
    """Fuzz the _PARSE_MEM_BYTES string parser."""
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
    try:
        _PARSE_MEM_BYTES(s)
    except (ValueError, KeyError, IndexError, OverflowError, TypeError):
        pass


def fuzz_text_processing(fdp):
    """Fuzz find_printable_text and _is_chinese_char."""
    choice = fdp.ConsumeIntInRange(0, 1)
    if choice == 0:
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            find_printable_text(text)
        except (IndexError, ValueError, TypeError, OverflowError):
            pass
    else:
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        try:
            _is_chinese_char(cp)
        except (ValueError, TypeError, OverflowError):
            pass


@atheris.instrument_func
def TestOneInput(data):
    if len(data) < 2:
        return
    fdp = atheris.FuzzedDataProvider(data)
    target = fdp.ConsumeIntInRange(0, 3)

    if target == 0:
        fuzz_deserialize_type(fdp)
    elif target == 1:
        fuzz_msgpack_deserialize(fdp)
    elif target == 2:
        fuzz_parse_mem_bytes(fdp)
    else:
        fuzz_text_processing(fdp)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
