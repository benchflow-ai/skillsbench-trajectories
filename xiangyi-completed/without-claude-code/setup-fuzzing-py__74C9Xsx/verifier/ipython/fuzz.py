"""
Fuzz driver for IPython library.
Focus: Code parsing and magic command processing
"""

from IPython.core.compilerop import CachingCompiler
from IPython.core.inputtransformer2 import TransformerManager, PromptStripper
import tokenize
import io
import time

def fuzz_caching_compiler(data):
    """Fuzz CachingCompiler.ast_parse() with Python code"""
    try:
        code = data.decode('utf-8', errors='ignore')
        compiler = CachingCompiler()
        try:
            compiler.ast_parse(code)
        except SyntaxError:
            pass
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_caching_compiler: {type(e).__name__}")

def fuzz_prompt_stripper(data):
    """Fuzz PromptStripper with various input lines"""
    try:
        text = data.decode('utf-8', errors='ignore')
        lines = text.split('\n')
        stripper = PromptStripper()
        try:
            stripper(lines)
        except Exception:
            pass
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_prompt_stripper: {type(e).__name__}")

def fuzz_transformer_manager(data):
    """Fuzz TransformerManager with code input"""
    try:
        code = data.decode('utf-8', errors='ignore')
        tm = TransformerManager()
        try:
            tm.transform_cell(code)
        except (SyntaxError, ValueError):
            pass
    except (TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_transformer_manager: {type(e).__name__}")

def main():
    """Main fuzzing function"""
    test_cases = [
        b"x = 1",
        b"In [1]: print('hello')",
        b">>> x = 1",
        b"%timeit x",
        b"" * 100,
        b"for i in range(100):\n    pass",
        b"def f():\n    return 1",
    ]

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < 10:
        for test_data in test_cases:
            choice = iterations % 3
            if choice == 0:
                fuzz_caching_compiler(test_data)
            elif choice == 1:
                fuzz_prompt_stripper(test_data)
            else:
                fuzz_transformer_manager(test_data)
            iterations += 1

    print(f"IPython fuzzer: Completed {iterations} iterations in 10 seconds")

if __name__ == "__main__":
    main()
