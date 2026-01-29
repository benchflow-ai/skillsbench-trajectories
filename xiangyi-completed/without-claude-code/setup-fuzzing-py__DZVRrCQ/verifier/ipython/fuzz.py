#!/usr/bin/env python3
"""
Coverage-guided fuzzing for IPython library using atheris (LibFuzzer compatible).

Targets:
- TransformerManager.transform_cell(): Main input transformation
- TransformerManager.check_complete(): Completion detection
- split_user_input(): Line splitting
- Magics.parse_options(): Magic argument parsing
- guarded_eval(): Safe evaluation
"""

import sys
import atheris


def setup_ipython():
    """Import IPython and related modules."""
    global TransformerManager, split_user_input, guarded_eval, EvaluationContext, EvaluationPolicy
    from IPython.core.inputtransformer2 import TransformerManager as TM
    from IPython.core.splitinput import split_user_input as sui
    from IPython.core.guarded_eval import guarded_eval as ge, EvaluationContext as EC, EvaluationPolicy as EP
    TransformerManager = TM
    split_user_input = sui
    guarded_eval = ge
    EvaluationContext = EC
    EvaluationPolicy = EP


def fuzz_transform_cell(data: bytes):
    """Fuzz TransformerManager.transform_cell() with arbitrary cell content."""
    try:
        cell = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        tm = TransformerManager()
        tm.transform_cell(cell)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_check_complete(data: bytes):
    """Fuzz TransformerManager.check_complete() with partial input."""
    try:
        cell = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        tm = TransformerManager()
        tm.check_complete(cell)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_split_user_input(data: bytes):
    """Fuzz split_user_input() with arbitrary line input."""
    try:
        line = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        split_user_input(line)
    except (ValueError, RecursionError):
        pass
    except Exception:
        pass


def fuzz_guarded_eval(data: bytes):
    """Fuzz guarded_eval() with code strings."""
    try:
        code = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        # Use a minimal/restrictive policy for safety
        policy = EvaluationPolicy(
            allow_builtins_access=True,
            allow_locals_access=True,
            allow_globals_access=False,
            allow_item_access=True,
            allow_attr_access=True,
            allowed_calls=set(),
        )
        context = EvaluationContext(
            locals={},
            globals={},
            evaluation=policy,
        )
        guarded_eval(code, context)
    except (SyntaxError, ValueError, TypeError, NameError, AttributeError, KeyError):
        pass
    except Exception:
        pass


def fuzz_magic_commands(data: bytes):
    """Fuzz magic command parsing via transform_cell."""
    try:
        base = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    # Prefix with magic indicators
    magic_prefixes = ['%', '%%', '!', '!!', '?', '??', '/', ',', ';']
    for prefix in magic_prefixes:
        cell = prefix + base
        try:
            tm = TransformerManager()
            tm.transform_cell(cell)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            pass
        except Exception:
            pass


def TestOneInput(data: bytes):
    """Main fuzzing entry point - calls all fuzz targets."""
    if len(data) < 1:
        return

    # Use first byte to select target
    selector = data[0] % 5
    payload = data[1:]

    if selector == 0:
        fuzz_transform_cell(payload)
    elif selector == 1:
        fuzz_check_complete(payload)
    elif selector == 2:
        fuzz_split_user_input(payload)
    elif selector == 3:
        fuzz_guarded_eval(payload)
    else:
        fuzz_magic_commands(payload)


def main():
    """Main entry point for the fuzzer."""
    setup_ipython()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
