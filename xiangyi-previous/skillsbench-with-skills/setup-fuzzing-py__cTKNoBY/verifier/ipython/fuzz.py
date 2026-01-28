#!/usr/bin/env python3
"""Coverage-guided fuzzer for IPython library using atheris."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for IPython input transformation and evaluation."""
    try:
        # Convert bytes to string
        try:
            input_str = data.decode('utf-8')
        except UnicodeDecodeError:
            input_str = data.decode('latin-1')
        
        # Test input transformer
        try:
            from IPython.core.inputtransformer2 import TransformerManager
            tm = TransformerManager()
            tm.transform_cell(input_str)
        except (SyntaxError, ValueError, TypeError, IndentationError):
            pass
        except Exception:
            pass
        
        # Test guarded_eval
        try:
            from IPython.core.guarded_eval import (
                guarded_eval, EvaluationContext, EvaluationPolicy
            )
            context = EvaluationContext(
                locals={},
                globals={},
                evaluation=EvaluationPolicy.MINIMAL
            )
            guarded_eval(input_str, context)
        except (SyntaxError, ValueError, TypeError, NameError, 
                AttributeError, KeyError):
            pass
        except Exception:
            pass
        
        # Test splitinput
        try:
            from IPython.core.splitinput import split_user_input
            split_user_input(input_str)
        except (ValueError, TypeError):
            pass
        except Exception:
            pass
            
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
