import sys
sys.dont_write_bytecode = True

import os
import importlib.util
import atheris

# We cannot use normal imports because the minisgl package __init__.py files
# import torch and other heavy dependencies. Instead, load the specific
# source files directly.
_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python", "minisgl")


def _load_module_from_file(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load env.py directly (no problematic imports)
_env_mod = _load_module_from_file("minisgl_env", os.path.join(_base, "env.py"))
_PARSE_MEM_BYTES = _env_mod._PARSE_MEM_BYTES

# For detokenize.py, we extract the two pure functions directly from source
# because the module imports minisgl.message which transitively requires torch.
# We use ast to extract only _is_chinese_char and find_printable_text.
import ast as _ast
import textwrap as _textwrap

_detok_path = os.path.join(_base, "tokenizer", "detokenize.py")
_detok_source = open(_detok_path).read()
_detok_tree = _ast.parse(_detok_source)

_detok_ns = {}
for _node in _ast.iter_child_nodes(_detok_tree):
    if isinstance(_node, _ast.FunctionDef) and _node.name in (
        "_is_chinese_char", "find_printable_text"
    ):
        _func_source = _ast.get_source_segment(_detok_source, _node)
        exec(compile(_func_source, _detok_path, "exec"), _detok_ns)

_is_chinese_char = _detok_ns["_is_chinese_char"]
find_printable_text = _detok_ns["find_printable_text"]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # ---- Target 1: _PARSE_MEM_BYTES ----
    # Consume a unicode string for memory-size parsing.
    mem_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
    try:
        result = _PARSE_MEM_BYTES(mem_str)
        # If no exception, the result must be an int.
        assert isinstance(result, int), f"Expected int, got {type(result)}"
    except (ValueError, KeyError, IndexError):
        # These are expected failures for malformed input strings.
        pass

    # ---- Target 2: _is_chinese_char ----
    # Consume an integer codepoint.  Valid Unicode range is 0..0x10FFFF but
    # the function accepts any int, so we also test outside that range.
    cp = fdp.ConsumeIntInRange(-1, 0x110000)
    result_cjk = _is_chinese_char(cp)
    # The function must always return a bool.
    assert isinstance(result_cjk, bool), f"Expected bool, got {type(result_cjk)}"

    # ---- Target 3: find_printable_text ----
    # Consume a unicode string for printable-text extraction.
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
    result_text = find_printable_text(text)
    # Invariant: the returned text must never be longer than the input.
    assert len(result_text) <= len(text), (
        f"Output longer than input: {len(result_text)} > {len(text)}"
    )
    # Invariant: if the input ends with a newline the full input is returned.
    if text.endswith("\n"):
        assert result_text == text, (
            f"Text ending with newline should be returned as-is"
        )


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
